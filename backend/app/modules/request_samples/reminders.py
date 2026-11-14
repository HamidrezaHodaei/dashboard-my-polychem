"""
Daily reminders of the Request Sample workflow.

Like the task deadline warnings they are generated lazily when the user's notification list is
fetched (the header polls it) -- no scheduler needed. One decision table drives everything, keyed on
the request's CURRENT status / stage, so a user never gets a reminder that no longer applies:

  stage (status)                          reminder  → who                         stops when
  ──────────────────────────────────────  ────────  ──────────────────────────  ─────────────────────────────────
  APPROVED  (not shipped yet)             ship      sales rep                     shipment recorded → «ارسال‌شده»
  DISPATCHED (shipped, not received)      deliver   sales rep                     receipt confirmed
  AWAITING_FEEDBACK (received), the latest
    follow-up has no next date / none yet followup  follow-up responsible / rep    a follow-up WITH a next date is saved
  AWAITING_FEEDBACK, next date == today   due       follow-up responsible / rep   (one notice on that date)
  AWAITING_FEEDBACK, next date passed     followup  follow-up responsible / rep   a new follow-up is recorded

Rules that prevent duplicate / irrelevant notices:
* at most ONE notice per (request, kind, day): the dedupe key is `rs:<kind>:<request id>:<date>`;
* when a new daily notice of a kind is created, the older UNREAD ones of that request+kind are marked read;
* every transition that leaves a stage calls `clear()` so stale unread reminders disappear at once;
* nothing is sent for DRAFT / PENDING_APPROVAL / ON_HOLD / closed requests, to inactive users, or once the
  customer's final feedback is decided.

SHIP_REMINDER_FROM: reminders about shipping start when the request is APPROVED (before approval nobody
can ship it). Add S.PENDING_APPROVAL to SHIP_STATUSES if they must start at submission.
"""
from datetime import date

from sqlalchemy import exists, or_

from app.core.users.models import User
from app.extensions import db
from app.modules.notifications import services as notifications
from app.modules.notifications.models import Notification
from app.modules.request_samples.models import RequestSample, RequestSampleFollowUp, SampleStatus
from app.utils.jalali import format_jalali, tehran_today

S = SampleStatus
SHIP_STATUSES = (S.APPROVED.value,)
OPEN_FEEDBACK = (None, "UNDER_EVALUATION", "NO_RESPONSE")
KINDS = ("ship", "deliver", "followup", "due")
TYPES = {
    "ship": "SAMPLE_REMIND_SHIP", "deliver": "SAMPLE_REMIND_DELIVER",
    "followup": "SAMPLE_REMIND_FOLLOWUP", "due": "SAMPLE_FOLLOWUP_DUE",
}


def _fa(value) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _owner(req: RequestSample) -> int | None:
    return req.sales_rep_user_id or req.created_by_user_id


def due_reminder(req: RequestSample, today: date) -> tuple[str, int | None, str, str] | None:
    """(kind, recipient user id, title, body) that applies to `req` today -- or None."""
    code = req.code
    customer = req.customer.display_name if req.customer else ""
    who = f" ({customer})" if customer else ""
    if req.status in SHIP_STATUSES:
        return ("ship", _owner(req), "نمونه هنوز ارسال نشده است",
                f"درخواست نمونهٔ {code}{who} تأیید شده اما اطلاعات ارسال آن ثبت نشده است. پس از تحویل نمونه به واحد ارسال / شرکت حمل، «ارسال‌شده» را ثبت کنید.")
    if req.status == S.DISPATCHED.value:
        return ("deliver", _owner(req), "تحویل نمونه به مشتری تأیید نشده است",
                f"نمونهٔ درخواست {code}{who} ارسال شده اما دریافت آن توسط مشتری هنوز تأیید نشده است.")
    if req.status == S.AWAITING_FEEDBACK.value and req.fb_status in OPEN_FEEDBACK:
        latest = req.followups[-1] if req.followups else None
        nxt = latest.next_followup_date if latest else None
        who_id = (latest.responsible_user_id if latest else None) or _owner(req)
        if nxt is None:
            why = "هنوز پیگیری ثبت نشده" if latest is None else "تاریخ پیگیری بعدی مشخص نشده"
            return ("followup", _owner(req), "پیگیری مشتری لازم است",
                    f"نمونهٔ درخواست {code}{who} به مشتری رسیده اما {why} است.")
        if nxt == today:
            return ("due", who_id, "امروز موعد پیگیری مشتری است",
                    f"پیگیری برنامه‌ریزی‌شدهٔ درخواست نمونهٔ {code}{who} برای امروز است.")
        if nxt < today:
            return ("followup", who_id, "موعد پیگیری مشتری گذشته است",
                    f"موعد پیگیری درخواست نمونهٔ {code}{who} ({_fa(format_jalali(nxt))}) گذشته و پیگیری جدیدی ثبت نشده است.")
    return None


def clear(request_id: int, kinds: tuple[str, ...] = KINDS) -> None:
    """Mark the unread reminders of `request_id` (of these kinds) as read -- called when a request
    leaves the stage they belong to. No commit: the caller's transaction owns it."""
    now = notifications._utcnow()
    for kind in kinds:
        db.session.query(Notification).filter(
            Notification.read_at.is_(None), Notification.dedupe_key.like(f"rs:{kind}:{request_id}:%"),
        ).update({Notification.read_at: now}, synchronize_session=False)


def generate_for(user_id: int) -> int:
    """Create today's reminders for `user_id`. Idempotent: safe to call on every poll."""
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return 0
    today = tehran_today()
    candidates = db.session.query(RequestSample).filter(
        RequestSample.deleted_at.is_(None),
        RequestSample.status.in_([*SHIP_STATUSES, S.DISPATCHED.value, S.AWAITING_FEEDBACK.value]),
        or_(
            RequestSample.sales_rep_user_id == user_id,
            RequestSample.created_by_user_id == user_id,
            exists().where(RequestSampleFollowUp.request_id == RequestSample.id,
                           RequestSampleFollowUp.responsible_user_id == user_id),
        ),
    ).all()
    created = 0
    for req in candidates:
        found = due_reminder(req, today)
        if found is None:
            continue
        kind, recipient, title, body = found
        if recipient != user_id:
            continue
        key = f"rs:{kind}:{req.id}:{today.isoformat()}"
        row = notifications.notify(
            user_id, TYPES[kind], title, body, link=f"/crm/request-samples/{req.id}", dedupe_key=key,
        )
        if row is None:
            continue
        # keep the bell clean: yesterday's unread reminder of this request+kind is superseded
        db.session.query(Notification).filter(
            Notification.user_id == user_id, Notification.read_at.is_(None),
            Notification.dedupe_key.like(f"rs:{kind}:{req.id}:%"), Notification.dedupe_key != key,
        ).update({Notification.read_at: notifications._utcnow()}, synchronize_session=False)
        created += 1
    if created:
        db.session.commit()
    return created
