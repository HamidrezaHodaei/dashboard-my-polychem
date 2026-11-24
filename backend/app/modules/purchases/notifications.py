"""
Purchase-flow notifications: who must hear about which step of a purchase request.

`flow._ev()` is called for every recorded step (request status change or item status change), so one hook there
covers the whole workflow. The bell entry and -- through the push outbox -- the phone notification are created by
the shared `notifications.services.notify()`; nothing here knows about push.

Recipients (the actor is never notified about their own action):
    new / resubmitted request  -> procurement      item sent to the manager  -> managers
    manager approved           -> finance          manager sent an item back -> procurement
    payment recorded           -> procurement      returned / void / sourcing / completed,
                                                   shipping / delivered / item cancelled -> the requester (warehouse user)
Several items moving in one action produce ONE notification per recipient and kind.
"""
import logging

from app.core.users.models import User
from app.extensions import db
from app.modules.notifications import services as notifications
from app.modules.purchases import services as S
from app.modules.purchases.models import ItemStatus as IS
from app.modules.purchases.models import PurchaseRequest, PurchaseStatus as PS

log = logging.getLogger("polychem.purchases.notify")


def _holders(action: str) -> list[int]:
    """Active users who hold the purchase permission `action` (cached for the current transaction)."""
    cache = db.session.info.setdefault("_pf_holders", {})
    if action not in cache:
        users = db.session.query(User).filter(User.is_active.is_(True), User.deleted_at.is_(None)).all()
        cache[action] = [u.id for u in users if S.can(u, action)]
    return cache[action]


def _val(x):
    return getattr(x, "value", x)


def _plan(req: PurchaseRequest, item, kind: str, frm, to, note: str | None):
    """-> (recipients, type, title, body) or None when this step needs no notification."""
    unit = f" از واحد «{req.requester_unit}»" if getattr(req, "requester_unit", None) else ""
    ref = f"درخواست خرید {req.request_no}"
    to, frm = _val(to), _val(frm)
    creator = [req.created_by_user_id] if req.created_by_user_id else []
    if kind == "STATUS":
        if to == PS.UNDER_REVIEW.value and frm is None:
            return _holders("procure"), "PURCHASE_NEW", "درخواست خرید جدید", f"{ref}{unit} ثبت شد و در کارتابل تدارکات منتظر بررسی است."
        if to == PS.UNDER_REVIEW.value and frm == PS.RETURNED.value:
            return _holders("procure"), "PURCHASE_RESUBMITTED", "درخواست خرید اصلاح شد", f"{ref} پس از اصلاح دوباره برای تدارکات ارسال شد."
        if to == PS.RETURNED.value:
            return creator, "PURCHASE_RETURNED", "درخواست خرید برای اصلاح برگشت خورد", f"{ref}: {note or 'لطفاً اطلاعات را اصلاح و دوباره ارسال کنید.'}"
        if to == PS.VOID.value:
            return creator, "PURCHASE_VOID", "درخواست خرید ابطال شد", f"{ref}" + (f": {note}" if note else " ابطال شد.")
        if to == PS.SOURCING.value:
            return creator, "PURCHASE_STATUS", "درخواست خرید در مرحلهٔ تأمین است", f"{ref} وارد مرحلهٔ استعلام و تأمین شد."
        if to == PS.COMPLETED.value:
            return creator, "PURCHASE_STATUS", "درخواست خرید تکمیل شد", f"همهٔ کالاهای {ref} تحویل شد."
        return None
    if to == IS.AWAITING_APPROVAL.value:
        return _holders("manager"), "PURCHASE_APPROVAL", "درخواست خرید منتظر تأیید شما است", f"{ref}{unit} برای تصمیم مدیر ارسال شد."
    if to == IS.IN_FINANCE.value:
        return _holders("finance"), "PURCHASE_FINANCE", "درخواست خرید برای پرداخت ارجاع شد", f"{ref} توسط مدیر تأیید شد و منتظر پرداخت است."
    if to == IS.INQUIRY.value and frm == IS.AWAITING_APPROVAL.value:
        return _holders("procure"), "PURCHASE_MANAGER_RETURN", "مدیر یک کالا را به تدارکات برگرداند", f"{ref}: {note or 'نیاز به بازنگری استعلام دارد.'}"
    if to == IS.PAID.value:
        return _holders("procure"), "PURCHASE_PAID", "پرداخت انجام شد", f"پرداخت کالای {ref} ثبت شد؛ ادامهٔ تأمین با تدارکات است."
    if to in (IS.SHIPPING.value, IS.DELIVERED.value):
        word = "در حال حمل است" if to == IS.SHIPPING.value else "تحویل شد"
        return creator, "PURCHASE_STATUS", f"کالای درخواست خرید {word}", f"یکی از کالاهای {ref} {word}."
    if to == IS.CANCELLED.value and req.status != PS.VOID:
        return creator, "PURCHASE_STATUS", "یکی از کالاهای درخواست خرید لغو شد", f"{ref}: {note or 'کالا لغو شد.'}"
    return None


def on_event(req: PurchaseRequest, actor: User, *, item, kind: str, from_status, to_status, note: str | None) -> None:
    """Called by flow._ev() inside the caller's transaction (no commit). Never raises."""
    try:
        plan = _plan(req, item, kind, from_status, to_status, note)
        if not plan:
            return
        recipients, type_, title, body = plan
        sent = db.session.info.setdefault("_pf_sent", set())
        for uid in dict.fromkeys(recipients):
            if not uid or uid == actor.id or (uid, req.id, type_) in sent:
                continue
            sent.add((uid, req.id, type_))
            notifications.notify(uid, type_, title, body, link=f"/procurement/purchases/flow/{req.id}")
    except Exception:  # noqa: BLE001 - a notification problem must never block the purchase workflow
        log.exception("purchase notification failed")
