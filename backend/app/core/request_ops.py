"""
Database-side half of the shared request workflow (see request_workflow.py for the rules).
Used by the suppliers and customers services; logistics has its own copy because its
status lives in an enum column. Each function changes the record and queues notifications;
the CALLER writes the audit log and commits.
"""
from datetime import datetime, timezone

from app.core import request_workflow as wf
from app.modules.notifications import services as notifications
from app.permissions.exceptions import PermissionDeniedError
from app.utils.exceptions import ConflictError


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def creator_may_edit(rec, actor_id: int) -> bool:
    return wf.creator_can_edit(
        created_by_user_id=rec.created_by_user_id, actor_id=actor_id,
        status=rec.review_status, is_finalized=rec.is_finalized,
    )


def viewer_flags(rec, actor_id: int, *, can_update: bool, can_review: bool) -> dict:
    mine = rec.created_by_user_id == actor_id
    return {
        "can_edit": can_update or creator_may_edit(rec, actor_id),
        "can_finalize": (can_update or mine) and (
            rec.review_status == wf.NEEDS_EDIT or (rec.review_status == wf.PENDING and not rec.is_finalized)
        ),
        "can_request_change": rec.change_request_note is None and wf.can_request_change(
            created_by_user_id=rec.created_by_user_id, actor_id=actor_id,
            status=rec.review_status, is_finalized=rec.is_finalized,
        ),
        "can_review": can_review,
    }


def finalize(rec, actor, *, can_update: bool, link: str) -> str:
    """ثبت نهایی (first submit) or ثبت مجدد (after corrections) -> back in the review queue."""
    if not (rec.created_by_user_id == actor.id or can_update):
        raise PermissionDeniedError("permission_denied", "Only the creator of this request can submit it.")
    if not (rec.review_status == wf.NEEDS_EDIT or (rec.review_status == wf.PENDING and not rec.is_finalized)):
        raise ConflictError("This request is already submitted.")
    resubmission = rec.review_status == wf.NEEDS_EDIT
    rec.review_status = wf.after_finalize(rec.review_status)
    rec.is_finalized = True
    if hasattr(rec, "finalized_at"):
        rec.finalized_at = _now()
    if hasattr(rec, "finalized_by_user_id"):
        rec.finalized_by_user_id = actor.id
    if resubmission and rec.decided_by_user_id and rec.decided_by_user_id != actor.id:
        notifications.notify(
            rec.decided_by_user_id, "REVIEW_RESUBMITTED", "درخواست پس از اصلاح دوباره ثبت شد",
            f"«{rec.display_name}» پس از اعمال اصلاحات دوباره برای بررسی ثبت شد.", link=link,
        )
    return "resubmit" if resubmission else "finalize"


def request_change(rec, actor, reason: str, *, link: str) -> None:
    if not wf.can_request_change(
        created_by_user_id=rec.created_by_user_id, actor_id=actor.id,
        status=rec.review_status, is_finalized=rec.is_finalized,
    ):
        raise PermissionDeniedError("permission_denied", "You cannot request a change for this record.")
    rec.change_request_note = reason
    rec.change_requested_at = _now()
    if rec.decided_by_user_id and rec.decided_by_user_id != actor.id:
        notifications.notify(
            rec.decided_by_user_id, "CHANGE_REQUEST", "درخواست تغییر اطلاعات",
            f"{actor.full_name} برای «{rec.display_name}» درخواست تغییر اطلاعات ثبت کرد: {reason}", link=link,
        )


def review(rec, actor, action: str, note: str | None, *, link: str) -> tuple[str, str]:
    """A manager decides. Returns (from, to)."""
    if action in wf.NOTE_REQUIRED and not note:
        raise ConflictError("A written reason is required for this decision.")
    if not rec.is_finalized:
        raise ConflictError("This request is still a draft: its creator has not submitted it yet.")
    nxt = wf.next_status_on_review(action, rec.review_status)
    if nxt is None:
        raise ConflictError(f"Cannot {action.lower()} a request whose status is {rec.review_status}.")
    previous = rec.review_status
    rec.review_status = nxt
    rec.review_note = note
    rec.decided_by_user_id = actor.id
    rec.decided_at = _now()
    rec.change_request_note = rec.change_requested_at = None  # the request has been answered
    if rec.created_by_user_id and rec.created_by_user_id != actor.id:
        title, body = wf.review_notification(action, rec.display_name, note)
        notifications.notify(rec.created_by_user_id, "REVIEW_RESULT", title, body, link=link)
    return previous, nxt
