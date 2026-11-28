"""
Read-only "activity" views for the user-management area:

  - per-user session list (login / logout / IP / device / OS / browser)
  - per-user activity timeline (audit_logs rows written by that user)
  - cross-user login/logout event list

Everything here is READ-ONLY and built from rows the system already wrote (audit_logs,
user_sessions). Nothing is estimated: a value the server never recorded is returned as null
and the UI renders it as "ثبت نشده".

Access: the same permission and scope as reading the user himself (`core.user.read`), so a
department manager can only see people in the scopes their grant covers.

Date filters (`date_from` / `date_to`) are calendar days in Tehran ("YYYY-MM-DD", inclusive) --
the UI converts the Jalali dates the person typed to these. Timestamps in the DB are UTC.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from app.core.audit_logs.models import AuditLog
from app.core.auth.models import RefreshToken, UserSession
from app.core.authorization.models import ScopeType
from app.core.teams.models import TeamMember
from app.core.users import services as user_services
from app.core.users.models import User
from app.extensions import db
from app.permissions.service import get_matching_grants
from app.utils.exceptions import ConflictError
from app.utils.jalali import TEHRAN
from app.utils.pagination import paginate_query

AUTH_ACTIONS = ("login_success", "login_failure", "logout")
# audit events that are noise for a person-facing timeline (the token silently renewing itself)
_HIDDEN_ACTIONS = ("refresh_success", "refresh_reuse_detected", "refresh_revoked")
_SAFE_META_KEYS = ("device_type", "os", "browser", "user_agent", "session_id", "reason", "revoked_count")


def iso_utc(value: datetime | None) -> str | None:
    """DB timestamps are naive UTC; always send an explicit offset so the UI can't misread them."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_day(value: str | None, name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ConflictError(f"'{name}' must be a date like 2026-11-24.") from exc


def _tehran_day_start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=TEHRAN).astimezone(timezone.utc).replace(tzinfo=None)


def _apply_range(query, column, date_from: date | None, date_to: date | None):
    if date_from is not None:
        query = query.filter(column >= _tehran_day_start_utc(date_from))
    if date_to is not None:  # inclusive of the whole last day
        query = query.filter(column < _tehran_day_start_utc(date_to + timedelta(days=1)))
    return query


def _meta(row: AuditLog) -> dict:
    meta = row.event_metadata if isinstance(row.event_metadata, dict) else {}
    return {k: meta[k] for k in _SAFE_META_KEYS if k in meta and not isinstance(meta[k], (dict, list))}


def _changed_fields(row: AuditLog) -> list[str]:
    """Names of the fields a mutating action touched (never their values -- a diff can hold personal data)."""
    meta = row.event_metadata if isinstance(row.event_metadata, dict) else {}
    for key in ("changes", "diff", "fields", "updated_fields"):
        value = meta.get(key)
        if isinstance(value, dict):
            return [str(k) for k in value][:20]
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return value[:20]
    return []


def _event(row: AuditLog) -> dict:
    meta = _meta(row)
    return {
        "id": row.id,
        "at": iso_utc(row.created_at),
        "action": row.action,
        "module": row.module,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "category": "auth" if row.module == "auth" else "action",
        "ip_address": row.ip_address,
        "device_type": meta.get("device_type"),
        "os": meta.get("os"),
        "browser": meta.get("browser"),
        "session_id": meta.get("session_id"),
        "reason": meta.get("reason"),
        "changed_fields": _changed_fields(row),
    }


# ---------------------------------------------------------------------
# Per-user
# ---------------------------------------------------------------------


def _readable_user(actor: User, user_id: int) -> User:
    return user_services.get_user(actor, user_id)  # 404 / 403 exactly like opening the user


def _session_status(session: UserSession, live_until: datetime | None, now: datetime) -> str:
    if session.logout_at is not None:
        return "ended"
    if live_until is not None and live_until > now:
        return "active"
    return "expired"


def list_sessions(actor: User, user_id: int, *, page: int, per_page: int, status: str | None = None) -> dict:
    user = _readable_user(actor, user_id)
    now = datetime.utcnow()

    base = db.session.query(UserSession).filter(UserSession.user_id == user.id)
    live = dict(
        db.session.query(RefreshToken.session_id, db.func.max(RefreshToken.expires_at))
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None), RefreshToken.session_id.isnot(None))
        .group_by(RefreshToken.session_id).all()
    )
    if status in {"active", "ended", "expired"}:
        rows_all = base.order_by(UserSession.login_at.desc()).all()
        rows_all = [s for s in rows_all if _session_status(s, live.get(s.id), now) == status]
        total = len(rows_all)
        rows = rows_all[(page - 1) * per_page: page * per_page]
    else:
        rows, total = paginate_query(base.order_by(UserSession.login_at.desc(), UserSession.id.desc()), page, per_page)

    since = db.session.query(db.func.min(UserSession.login_at)).scalar()
    return {
        "items": [
            {
                "id": s.id,
                "status": _session_status(s, live.get(s.id), now),
                "ip_address": s.ip_address,
                "device_type": s.device_type,
                "os": s.os,
                "browser": s.browser,
                "login_at": iso_utc(s.login_at),
                "last_seen_at": iso_utc(s.last_seen_at),
                "logout_at": iso_utc(s.logout_at),
                "logout_reason": s.logout_reason,
            }
            for s in rows
        ],
        "total": total,
        # sessions older than this were never recorded (the feature started then)
        "recording_since": iso_utc(since),
    }


def list_timeline(
    actor: User, user_id: int, *, page: int, per_page: int, q: str | None = None,
    category: str | None = None, date_from: str | None = None, date_to: str | None = None,
    sort: str = "newest",
) -> dict:
    user = _readable_user(actor, user_id)
    query = db.session.query(AuditLog).filter(
        AuditLog.user_id == user.id, AuditLog.action.notin_(_HIDDEN_ACTIONS)
    )
    if category == "auth":
        query = query.filter(AuditLog.module == "auth")
    elif category == "action":
        query = query.filter(AuditLog.module != "auth")
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter(db.or_(
            db.func.lower(AuditLog.action).like(like),
            db.func.lower(AuditLog.module).like(like),
            db.func.lower(db.func.coalesce(AuditLog.entity_type, "")).like(like),
            db.func.coalesce(AuditLog.ip_address, "").like(like),
        ))
    query = _apply_range(query, AuditLog.created_at, _parse_day(date_from, "date_from"), _parse_day(date_to, "date_to"))
    order = (AuditLog.created_at.asc(), AuditLog.id.asc()) if sort == "oldest" else (AuditLog.created_at.desc(), AuditLog.id.desc())
    rows, total = paginate_query(query.order_by(*order), page, per_page)
    first_audit = db.session.query(db.func.min(AuditLog.created_at)).filter(AuditLog.user_id == user.id).scalar()
    return {
        "items": [_event(r) for r in rows],
        "total": total,
        "first_event_at": iso_utc(first_audit),
    }


# ---------------------------------------------------------------------
# Across users: login / logout events
# ---------------------------------------------------------------------


def _readable_users_filter(actor: User):
    """Same visibility rule as list_users (GLOBAL sees everyone; otherwise department/org/team scopes)."""
    user_services._require(actor, "read", None, None)
    grants = get_matching_grants(actor, "core.user.read")
    if any(g.scope_type == ScopeType.GLOBAL for g in grants):
        return None
    dept_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.DEPARTMENT}
    org_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}
    team_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.TEAM}
    conditions = []
    if dept_ids:
        conditions.append(User.department_id.in_(dept_ids))
    if org_ids:
        conditions.append(User.organization_id.in_(org_ids))
    if team_ids:
        conditions.append(User.id.in_(
            db.session.query(TeamMember.user_id).filter(TeamMember.team_id.in_(team_ids))
        ))
    return db.or_(*conditions) if conditions else db.false()


def list_login_events(
    actor: User, *, page: int, per_page: int, q: str | None = None, event: str | None = None,
    user_id: int | None = None, date_from: str | None = None, date_to: str | None = None,
    sort: str = "newest",
) -> dict:
    scope = _readable_users_filter(actor)
    query = (
        db.session.query(AuditLog, User)
        .join(User, User.id == AuditLog.user_id)
        .filter(AuditLog.module == "auth", AuditLog.action.in_(AUTH_ACTIONS), User.deleted_at.is_(None))
    )
    if scope is not None:
        query = query.filter(scope)
    if event in AUTH_ACTIONS:
        query = query.filter(AuditLog.action == event)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.filter(db.or_(
            db.func.lower(User.full_name).like(like),
            db.func.lower(User.username).like(like),
            db.func.coalesce(AuditLog.ip_address, "").like(like),
        ))
    query = _apply_range(query, AuditLog.created_at, _parse_day(date_from, "date_from"), _parse_day(date_to, "date_to"))
    order = (AuditLog.created_at.asc(), AuditLog.id.asc()) if sort == "oldest" else (AuditLog.created_at.desc(), AuditLog.id.desc())
    rows, total = paginate_query(query.order_by(*order), page, per_page)
    items = []
    for log, user in rows:
        item = _event(log)
        item["user"] = {"id": user.id, "full_name": user.full_name, "username": user.username}
        items.append(item)
    return {"items": items, "total": total}
