"""
Web Push (RFC 8030 / 8291 / 8292 -- VAPID) for the notification system.

How a push happens
------------------
1. Any module creates an in-app notification with `notifications.services.notify(...)` inside its own
   transaction -- unchanged. A mapper hook notes every inserted Notification id; once the transaction COMMITS
   the ids are parked on `flask.g` (a rolled-back notification never reaches a phone).
2. The `after_request` hook (or, in the CLI, `flush_pending()`) turns the parked ids into OUTBOX rows
   (`push_deliveries`: one per notification x active device, unique pair => no duplicates) honouring the user's
   settings, then sends them -- from a short background thread in production so the HTTP response is not delayed.
3. Each delivery is re-checked at send time (device still bound to the same user, notification still unread,
   user still allowed to see the task, preferences unchanged), claimed atomically, sent, and classified:
      201/200/202  SENT                          404/410  EXPIRED -> device switched off
      401/403      FAILED  -> device switched off (VAPID key mismatch)      400/413  FAILED
      429/5xx/network error -> retried with back-off (1m, 5m, 30m, 2h, 6h), FAILED after PUSH_MAX_ATTEMPTS
4. `flask push-tick` (cron, every 1-5 min) generates deadline/follow-up reminders for users who have a device
   (the bell only creates them when the page is open), sends whatever is due (retries, quiet-hours leftovers)
   and prunes old rows.

Nothing private leaves the server except the payload below, encrypted end-to-end for the device by the Web Push
protocol; with "hide preview" on, even the title is generic.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlparse

from flask import current_app, g, has_app_context
from sqlalchemy import event, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from app.extensions import db
from app.modules.notifications import catalog
from app.modules.notifications.models import (
    Notification, NotificationPreference, NotificationSetting, PushDelivery, PushSubscription,
)
from app.utils.exceptions import InvalidInputError
from app.utils.jalali import TEHRAN

log = logging.getLogger("polychem.push")

BACKOFF_MINUTES = (1, 5, 30, 120, 360)
CLAIM_MINUTES = 10  # a claimed-but-never-finished delivery (process killed) becomes retryable after this
MAX_DEVICES_PER_USER = 10
GENERIC_TITLE = "اعلان جدید در پلیکم"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── configuration ───────────────────────────────────────────────────────────────────────────────
def is_configured() -> bool:
    c = current_app.config
    return bool(c.get("VAPID_PUBLIC_KEY") and c.get("VAPID_PRIVATE_KEY") and c.get("VAPID_SUBJECT"))


def public_key() -> str:
    return current_app.config.get("VAPID_PUBLIC_KEY", "")


def generate_vapid_keys() -> tuple[str, str]:
    """(public, private) as unpadded base64url -- the exact formats the browser and pywebpush expect."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    raw_private = key.private_numbers().private_value.to_bytes(32, "big")
    raw_public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64e(raw_public), _b64e(raw_private)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


# ── per-user settings ───────────────────────────────────────────────────────────────────────────
@dataclass
class Settings:
    push_enabled: bool = True
    show_preview: bool = True
    quiet_enabled: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "07:00"


def get_settings(user_id: int) -> Settings:
    row = db.session.get(NotificationSetting, user_id)
    if row is None:
        return Settings()
    return Settings(row.push_enabled, row.show_preview, row.quiet_enabled, row.quiet_start, row.quiet_end)


def disabled_categories(user_id: int) -> set[str]:
    rows = db.session.query(NotificationPreference.category).filter(
        NotificationPreference.user_id == user_id, NotificationPreference.push_enabled.is_(False)
    ).all()
    return {r[0] for r in rows}


_HM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _hm(value: str) -> time:
    m = _HM.match(value or "")
    if not m:
        return time(0, 0)
    return time(int(m.group(1)), int(m.group(2)))


def quiet_until(settings: Settings, now_utc: datetime) -> datetime | None:
    """If `now` falls inside the user's quiet hours (Tehran time), the UTC moment they end; else None."""
    if not settings.quiet_enabled:
        return None
    start, end = _hm(settings.quiet_start), _hm(settings.quiet_end)
    if start == end:
        return None
    local = now_utc.replace(tzinfo=timezone.utc).astimezone(TEHRAN)
    t = local.time().replace(tzinfo=None)
    inside = (start <= t < end) if start < end else (t >= start or t < end)
    if not inside:
        return None
    end_dt = datetime.combine(local.date(), end, tzinfo=TEHRAN)
    if end_dt <= local:
        end_dt += timedelta(days=1)
    return end_dt.astimezone(timezone.utc).replace(tzinfo=None)


def save_settings(user_id: int, *, push_enabled: bool, show_preview: bool, quiet_enabled: bool,
                  quiet_start: str, quiet_end: str, categories: dict[str, bool]) -> None:
    for label, value in (("quiet_start", quiet_start), ("quiet_end", quiet_end)):
        if not _HM.match(value or ""):
            raise InvalidInputError("ساعت را به شکل HH:MM وارد کنید.", label)
    unknown = [k for k in categories if k not in catalog.CATEGORY_KEYS]
    if unknown:
        raise InvalidInputError("دستهٔ اعلان نامعتبر است.", "categories")
    row = db.session.get(NotificationSetting, user_id)
    if row is None:
        row = NotificationSetting(user_id=user_id)
        db.session.add(row)
    row.push_enabled, row.show_preview, row.quiet_enabled = push_enabled, show_preview, quiet_enabled
    row.quiet_start, row.quiet_end = quiet_start, quiet_end
    existing = {p.category: p for p in db.session.query(NotificationPreference).filter_by(user_id=user_id)}
    for key, on in categories.items():
        pref = existing.get(key)
        if pref is None:
            db.session.add(NotificationPreference(user_id=user_id, category=key, push_enabled=on))
        else:
            pref.push_enabled = on
    db.session.commit()


def preferences_for(user_id: int) -> dict:
    s = get_settings(user_id)
    off = disabled_categories(user_id)
    return {
        "push_enabled": s.push_enabled, "show_preview": s.show_preview,
        "quiet_enabled": s.quiet_enabled, "quiet_start": s.quiet_start, "quiet_end": s.quiet_end,
        "categories": [
            {**c, "push_enabled": c["key"] not in off} for c in catalog.CATEGORIES
        ],
    }


# ── devices (subscriptions) ─────────────────────────────────────────────────────────────────────
def validate_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        raise InvalidInputError("آدرس اشتراک نامعتبر است.", "endpoint")
    u = urlparse(endpoint)
    host = (u.hostname or "").lower()
    allowed = current_app.config.get("PUSH_ENDPOINT_ALLOWED_HOSTS") or []
    ok_host = any(host == h or host.endswith("." + h) for h in allowed)
    if u.scheme != "https" or u.username or u.password or u.port not in (None, 443) or not ok_host:
        raise InvalidInputError("این سرویس اعلان پشتیبانی نمی‌شود.", "endpoint")
    return endpoint


def _validate_keys(p256dh: str, auth: str) -> None:
    try:
        ok = len(_b64d(p256dh)) == 65 and _b64d(p256dh)[0] == 4 and len(_b64d(auth)) == 16
    except Exception:  # noqa: BLE001 - any decoding problem means invalid keys
        ok = False
    if not ok:
        raise InvalidInputError("کلیدهای اشتراک نامعتبر است.", "keys")


def describe_agent(ua: str | None) -> tuple[str, str]:
    """(platform, human label) from a User-Agent: 'android' / 'ios' / 'windows' / 'mac' / 'linux' / 'other'."""
    ua = ua or ""
    if re.search(r"iPhone|iPad|iPod", ua):
        platform, fa = "ios", "iOS"
    elif "Android" in ua:
        platform, fa = "android", "اندروید"
    elif "Windows" in ua:
        platform, fa = "windows", "ویندوز"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        platform, fa = "mac", "مک"
    elif "Linux" in ua:
        platform, fa = "linux", "لینوکس"
    else:
        platform, fa = "other", "دستگاه"
    if "Edg/" in ua or "EdgA/" in ua:
        browser = "Edge"
    elif "Firefox/" in ua or "FxiOS" in ua:
        browser = "Firefox"
    elif "SamsungBrowser" in ua:
        browser = "Samsung Internet"
    elif "Chrome/" in ua or "CriOS" in ua:
        browser = "Chrome"
    elif "Safari/" in ua:
        browser = "Safari"
    else:
        browser = "مرورگر"
    return platform, f"{browser} - {fa}"


def upsert_subscription(user_id: int, *, endpoint: str, p256dh: str, auth: str,
                        user_agent: str | None, label: str | None) -> PushSubscription:
    validate_endpoint(endpoint)
    _validate_keys(p256dh, auth)
    digest = hashlib.sha256(endpoint.encode()).hexdigest()
    platform, auto_label = describe_agent(user_agent)
    now = _utcnow()
    sub = db.session.query(PushSubscription).filter_by(endpoint_hash=digest).one_or_none()
    if sub is None:
        sub = PushSubscription(endpoint_hash=digest, endpoint=endpoint, user_id=user_id)
        db.session.add(sub)
    # An existing endpoint is re-bound to whoever is signed in now (shared computer): the previous user stops
    # receiving on it immediately. Unsent deliveries of the previous user are dropped by the user check at send.
    sub.user_id = user_id
    sub.p256dh, sub.auth = p256dh, auth
    sub.user_agent = (user_agent or "")[:300] or None
    sub.platform = platform
    sub.device_label = ((label or "").strip()[:100]) or sub.device_label or auto_label
    sub.last_seen_at = now
    sub.disabled_at = sub.disabled_reason = None
    sub.failure_count = 0
    db.session.flush()
    # keep the list short: switch off the least recently seen devices beyond the cap
    active = (
        db.session.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.disabled_at.is_(None))
        .order_by(PushSubscription.last_seen_at.desc(), PushSubscription.id.desc()).all()
    )
    for extra in active[MAX_DEVICES_PER_USER:]:
        extra.disabled_at, extra.disabled_reason = now, "device_limit"
    db.session.commit()
    return sub


def device_dict(sub: PushSubscription, current_hash: str | None = None) -> dict:
    def iso(dt):
        return None if dt is None else dt.replace(tzinfo=timezone.utc).isoformat()

    return {
        "id": sub.id, "label": sub.device_label, "platform": sub.platform,
        "created_at": iso(sub.created_at), "last_seen_at": iso(sub.last_seen_at),
        "last_success_at": iso(sub.last_success_at), "last_error": sub.last_error,
        "active": sub.disabled_at is None, "disabled_reason": sub.disabled_reason,
        "is_current": bool(current_hash and current_hash == sub.endpoint_hash),
        "endpoint_hash": sub.endpoint_hash,
    }


def list_devices(user_id: int, current_endpoint: str | None = None) -> list[dict]:
    cur = hashlib.sha256(current_endpoint.encode()).hexdigest() if current_endpoint else None
    rows = (
        db.session.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.disabled_at.is_(None))
        .order_by(PushSubscription.last_seen_at.desc(), PushSubscription.id.desc()).all()
    )
    return [device_dict(r, cur) for r in rows]


def remove_device(user_id: int, sub_id: int) -> bool:
    sub = db.session.get(PushSubscription, sub_id)
    if sub is None or sub.user_id != user_id:  # never reveal whether another user's id exists
        return False
    db.session.delete(sub)
    db.session.commit()
    return True


def detach_endpoint(user_id: int, endpoint: str) -> bool:
    """Sign-out / switch-off on this browser: forget the device for this user only."""
    digest = hashlib.sha256(endpoint.encode()).hexdigest()
    sub = db.session.query(PushSubscription).filter_by(endpoint_hash=digest, user_id=user_id).one_or_none()
    if sub is None:
        return False
    db.session.delete(sub)
    db.session.commit()
    return True


# ── payload ─────────────────────────────────────────────────────────────────────────────────────
def _safe_url(link: str | None) -> str:
    return link if link and link.startswith("/") and not link.startswith("//") else "/notifications"


def build_payload(n: Notification, settings: Settings, unread: int) -> dict:
    cat = catalog.category_of(n.type)
    payload = {
        "v": 1, "id": n.id, "type": n.type, "category": cat, "tag": f"n-{n.id}",
        "url": _safe_url(n.link), "unread": unread, "ts": datetime.now(timezone.utc).isoformat(),
        "preview": settings.show_preview,
    }
    if settings.show_preview:
        payload["title"] = (n.title or GENERIC_TITLE)[:100]
        payload["body"] = (n.body or "")[:160] or None
    else:
        payload["title"], payload["body"] = GENERIC_TITLE, None
    return payload


# ── sending ─────────────────────────────────────────────────────────────────────────────────────
def _webpush_send(sub: PushSubscription, payload: dict, *, urgency: str, topic: str | None) -> tuple[int | None, str | None]:
    """The only function that touches the network. Returns (http_status or None, error text or None)."""
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return None, "pywebpush_missing"
    cfg = current_app.config
    headers = {"Urgency": urgency}
    if topic:
        headers["Topic"] = topic
    try:
        resp = webpush(
            subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=cfg["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": cfg["VAPID_SUBJECT"]},
            ttl=int(cfg["PUSH_TTL_SECONDS"]),
            headers=headers,
            timeout=10,
        )
        return resp.status_code, None
    except WebPushException as exc:
        r = getattr(exc, "response", None)
        return (r.status_code if r is not None else None), f"{exc}"[:300]
    except Exception as exc:  # noqa: BLE001 - network/TLS/crypto problems are all "try again later"
        return None, f"{type(exc).__name__}: {exc}"[:300]


# replaced in tests; signature (sub, payload, urgency=, topic=) -> (status, error)
send_func = _webpush_send


def _disable(sub: PushSubscription, reason: str, now: datetime) -> None:
    sub.disabled_at, sub.disabled_reason = now, reason


def _record_failure(sub: PushSubscription, error: str | None, now: datetime) -> None:
    sub.failure_count = (sub.failure_count or 0) + 1
    sub.last_error_at, sub.last_error = now, (error or "")[:300] or None
    if sub.failure_count >= 10:
        _disable(sub, "too_many_failures", now)


def _skip_reason(n: Notification | None, sub: PushSubscription | None) -> str | None:
    from app.core.users.models import User

    if sub is None or sub.disabled_at is not None:
        return "device_disabled"
    if n is None:
        return "notification_gone"
    if sub.user_id != n.user_id:  # the browser now belongs to somebody else
        return "device_rebound"
    if n.read_at is not None:
        return "already_read"
    user = db.session.get(User, n.user_id)
    if user is None or not user.is_active or getattr(user, "deleted_at", None) is not None:
        return "user_inactive"
    s = get_settings(n.user_id)
    if not s.push_enabled or catalog.category_of(n.type) in disabled_categories(n.user_id):
        return "preference_off"
    if n.task_id:  # same rule as the bell: a task that left the user's unit must not leak its title
        from app.modules.notifications.services import _accessible_task_ids

        if n.task_id not in _accessible_task_ids(n.user_id, {n.task_id}):
            return "no_access"
    return None


def deliver(delivery_id: int) -> str | None:
    """Send one outbox row if it is due. Returns the resulting status, or None if someone else owns it."""
    cfg = current_app.config
    d = db.session.get(PushDelivery, delivery_id)
    if d is None or d.status != "PENDING":
        return d.status if d else None
    now = _utcnow()
    if d.next_attempt_at and d.next_attempt_at > now:
        return "PENDING"
    n = db.session.get(Notification, d.notification_id)
    sub = db.session.get(PushSubscription, d.subscription_id)
    reason = _skip_reason(n, sub)
    if reason:
        d.status, d.last_error = "SKIPPED", reason
        db.session.commit()
        return "SKIPPED"
    settings = get_settings(n.user_id)
    quiet_end = quiet_until(settings, now)
    if quiet_end:
        d.next_attempt_at = quiet_end
        db.session.commit()
        return "PENDING"

    # atomic claim: two processes (request thread + cron) can never send the same row
    claimed = db.session.query(PushDelivery).filter(
        PushDelivery.id == d.id, PushDelivery.status == "PENDING", PushDelivery.attempts == d.attempts,
        or_(PushDelivery.next_attempt_at.is_(None), PushDelivery.next_attempt_at <= now),
    ).update(
        {PushDelivery.attempts: d.attempts + 1, PushDelivery.next_attempt_at: now + timedelta(minutes=CLAIM_MINUTES)},
        synchronize_session=False,
    )
    db.session.commit()
    if claimed != 1:
        return None
    db.session.refresh(d)

    unread = db.session.query(db.func.count(Notification.id)).filter(
        Notification.user_id == n.user_id, Notification.read_at.is_(None)
    ).scalar() or 0
    payload = build_payload(n, settings, int(unread))
    urgency = "high" if n.type in catalog.HIGH_URGENCY else "normal"
    status, error = send_func(sub, payload, urgency=urgency, topic=f"n{n.id}")

    now = _utcnow()
    d.http_status = status
    if status is not None and 200 <= status < 300:
        d.status, d.sent_at, d.last_error, d.next_attempt_at = "SENT", now, None, None
        sub.last_success_at, sub.failure_count, sub.last_error = now, 0, None
    elif status in (404, 410):
        d.status, d.last_error, d.next_attempt_at = "EXPIRED", "subscription_gone", None
        _disable(sub, "gone", now)
    elif status in (401, 403):
        d.status, d.last_error, d.next_attempt_at = "FAILED", f"rejected_{status}", None
        _record_failure(sub, error or f"HTTP {status}", now)
        _disable(sub, "rejected", now)  # almost always a VAPID key that differs from the one used to subscribe
    elif status in (400, 413):
        d.status, d.last_error, d.next_attempt_at = "FAILED", (error or f"HTTP {status}")[:300], None
        _record_failure(sub, error, now)
    else:  # 429, 5xx, timeouts, DNS ... : transient
        _record_failure(sub, error or (f"HTTP {status}" if status else "network"), now)
        d.last_error = (error or (f"HTTP {status}" if status else "network"))[:300]
        if d.attempts >= int(cfg["PUSH_MAX_ATTEMPTS"]):
            d.status, d.next_attempt_at = "FAILED", None
        else:
            wait = BACKOFF_MINUTES[min(d.attempts - 1, len(BACKOFF_MINUTES) - 1)]
            d.next_attempt_at = now + timedelta(minutes=wait)
    db.session.commit()
    if d.status == "FAILED":
        log.warning("push delivery %s failed for subscription %s: %s", d.id, sub.id, d.last_error)
    return d.status


def send_test(user_id: int, sub_id: int) -> dict:
    """Immediate test push to one of the user's own devices (no bell entry is created)."""
    sub = db.session.get(PushSubscription, sub_id)
    if sub is None or sub.user_id != user_id or sub.disabled_at is not None:
        raise InvalidInputError("دستگاه پیدا نشد.", "id")
    payload = {
        "v": 1, "id": 0, "type": "TEST", "category": "other", "tag": f"test-{sub.id}", "preview": True,
        "title": "آزمایش اعلان پلیکم", "body": "اگر این پیام را می‌بینید، اعلان‌ها روی این دستگاه فعال است.",
        "url": "/settings/notifications", "unread": None, "ts": datetime.now(timezone.utc).isoformat(),
    }
    status, error = send_func(sub, payload, urgency="normal", topic=None)
    now = _utcnow()
    ok = status is not None and 200 <= status < 300
    if ok:
        sub.last_success_at, sub.failure_count, sub.last_error = now, 0, None
    elif status in (404, 410):
        _disable(sub, "gone", now)
    elif status in (401, 403):
        _record_failure(sub, error, now)
        _disable(sub, "rejected", now)
    else:
        _record_failure(sub, error or (f"HTTP {status}" if status else "network"), now)
    db.session.commit()
    return {"ok": ok, "status": status, "error": None if ok else (error or "ارسال ناموفق بود.")}


# ── outbox ──────────────────────────────────────────────────────────────────────────────────────
def queue_for(notification_ids: list[int]) -> list[int]:
    """Create outbox rows for freshly committed notifications; returns the ids that are due right now."""
    if not notification_ids:
        return []
    now = _utcnow()
    due_ids: list[int] = []
    created: list[PushDelivery] = []
    for n in db.session.query(Notification).filter(Notification.id.in_(notification_ids)).all():
        settings = get_settings(n.user_id)
        if not settings.push_enabled or catalog.category_of(n.type) in disabled_categories(n.user_id):
            continue
        subs = db.session.query(PushSubscription).filter(
            PushSubscription.user_id == n.user_id, PushSubscription.disabled_at.is_(None)
        ).all()
        hold_until = quiet_until(settings, now)
        for sub in subs:
            if db.session.query(PushDelivery.id).filter_by(notification_id=n.id, subscription_id=sub.id).first():
                continue
            row = PushDelivery(
                notification_id=n.id, subscription_id=sub.id, status="PENDING", attempts=0,
                next_attempt_at=hold_until or now,
            )
            db.session.add(row)
            created.append(row)
    try:
        db.session.commit()
    except IntegrityError:  # another worker queued the same pair first: it will send it
        db.session.rollback()
        return []
    for row in created:
        if row.next_attempt_at <= now:
            due_ids.append(row.id)
    return due_ids


def process(delivery_ids: list[int]) -> None:
    for did in delivery_ids:
        try:
            deliver(did)
        except Exception:  # noqa: BLE001 - one bad row must not stop the rest
            db.session.rollback()
            log.exception("push delivery %s crashed", did)


def process_due(limit: int = 200) -> dict:
    now = _utcnow()
    ids = [
        r[0] for r in db.session.query(PushDelivery.id).filter(
            PushDelivery.status == "PENDING",
            or_(PushDelivery.next_attempt_at.is_(None), PushDelivery.next_attempt_at <= now),
        ).order_by(PushDelivery.id).limit(limit).all()
    ]
    process(ids)
    sent = db.session.query(db.func.count(PushDelivery.id)).filter(
        PushDelivery.id.in_(ids), PushDelivery.status == "SENT"
    ).scalar() if ids else 0
    return {"due": len(ids), "sent": int(sent or 0)}


def prune(days: int = 30) -> int:
    cutoff = _utcnow() - timedelta(days=days)
    n = db.session.query(PushDelivery).filter(
        PushDelivery.status.in_(["SENT", "SKIPPED", "EXPIRED", "FAILED"]), PushDelivery.updated_at < cutoff
    ).delete(synchronize_session=False)
    db.session.query(PushSubscription).filter(
        PushSubscription.disabled_at.isnot(None), PushSubscription.disabled_at < cutoff - timedelta(days=30)
    ).delete(synchronize_session=False)
    db.session.commit()
    return int(n or 0)


def tick() -> dict:
    """What the cron runs: reminders for people who have a device, then everything that is due."""
    from app.core.users.models import User
    from app.modules.notifications import services

    user_ids = [
        r[0] for r in db.session.query(PushSubscription.user_id).join(User, User.id == PushSubscription.user_id).filter(
            PushSubscription.disabled_at.is_(None), User.is_active.is_(True)
        ).distinct().all()
    ]
    made = 0
    for uid in user_ids:
        try:
            made += services.run_generators(uid)
        except Exception:  # noqa: BLE001
            db.session.rollback()
            log.exception("reminder generation failed for user %s", uid)
    flush_pending(inline=True)
    stats = process_due()
    stats.update({"users": len(user_ids), "reminders": made, "pruned": prune()})
    return stats


# ── hooks: commit -> outbox -> send ─────────────────────────────────────────────────────────────
_PENDING = "push_pending_ids"
_hooks_installed = False


def flush_pending(inline: bool = False) -> None:
    """Queue and send what this request/command committed. Never raises."""
    if not has_app_context():
        return
    ids = g.pop(_PENDING, None)
    if not ids:
        return
    try:
        due = queue_for(sorted(set(ids)))
        if not due:
            return
        if inline or not current_app.config.get("PUSH_ASYNC", True):
            process(due)
            return
        app = current_app._get_current_object()

        def _run():
            with app.app_context():
                try:
                    process(due)
                finally:
                    db.session.remove()

        threading.Thread(target=_run, name="push-send", daemon=True).start()
    except Exception:  # noqa: BLE001 - push must never break the request that created the notification
        db.session.rollback()
        log.exception("push dispatch failed")


def install_hooks(app) -> None:
    global _hooks_installed
    if not _hooks_installed:
        _hooks_installed = True

        @event.listens_for(Notification, "after_insert")
        def _collect(mapper, connection, target):  # noqa: ARG001
            sess = object_session(target)
            if sess is not None:
                sess.info.setdefault("_push_new", []).append(target.id)

        @event.listens_for(Session, "after_commit")
        def _committed(session):
            ids = session.info.pop("_push_new", None)
            if ids and has_app_context() and is_configured():
                g.setdefault(_PENDING, []).extend(ids)

        @event.listens_for(Session, "after_rollback")
        def _rolled_back(session):
            session.info.pop("_push_new", None)

    @app.after_request
    def _dispatch_after_request(response):
        flush_pending()
        return response
