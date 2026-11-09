"""
Shared review workflow for "request" records: logistics registrations, suppliers and customers.

Statuses (the SAME four everywhere; logistics keeps its extra SUSPENDED for approved parties):

    PENDING     در انتظار بررسی        submitted, in the review queue
    APPROVED    تأیید                  a manager approved it
    REJECTED    رد درخواست             a manager rejected it
    NEEDS_EDIT  نیازمند ویرایش یا تکمیل اطلاعات   a manager sent it back, with a mandatory explanation

Who may change the record:

* A manager (holder of the module's `update` permission) -- as before, any time.
* The person who CREATED the record -- WITHOUT any `update` permission, only inside this workflow:
    - while it is PENDING and not yet finalised ("ثبت نهایی" not pressed): free editing;
    - while it is NEEDS_EDIT: free editing, then "ثبت مجدد" puts it back to PENDING;
    - once finalised (PENDING / APPROVED / REJECTED): read-only. The creator may instead send the
      manager a written "request to change" (reason required); the manager then decides to set
      the record to NEEDS_EDIT.

The module services call the pure helpers below; nothing here touches the database.
"""
PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
NEEDS_EDIT = "NEEDS_EDIT"

STATUS_LABELS = {
    PENDING: "در انتظار بررسی",
    APPROVED: "تأیید",
    REJECTED: "رد درخواست",
    NEEDS_EDIT: "نیازمند ویرایش یا تکمیل اطلاعات",
}

# review action -> {current status: new status}
TRANSITIONS: dict[str, dict[str, str]] = {
    "APPROVE": {PENDING: APPROVED},
    "REJECT": {PENDING: REJECTED, NEEDS_EDIT: REJECTED},
    "REQUEST_EDIT": {PENDING: NEEDS_EDIT, APPROVED: NEEDS_EDIT},
    "REOPEN": {REJECTED: PENDING},
}
NOTE_REQUIRED = {"REJECT", "REQUEST_EDIT"}  # the reason / what to fix is mandatory


def creator_can_edit(*, created_by_user_id: int | None, actor_id: int, status: str, is_finalized: bool) -> bool:
    if created_by_user_id is None or created_by_user_id != actor_id:
        return False
    return status == NEEDS_EDIT or (status == PENDING and not is_finalized)


def can_request_change(*, created_by_user_id: int | None, actor_id: int, status: str, is_finalized: bool) -> bool:
    """A finalised request the creator can no longer edit: they may ask the manager for a change."""
    if created_by_user_id is None or created_by_user_id != actor_id or not is_finalized:
        return False
    return status in (PENDING, APPROVED)


def next_status_on_review(action: str, status: str) -> str | None:
    return TRANSITIONS.get(action, {}).get(status)


def after_finalize(status: str) -> str:
    """Submitting (or re-submitting) always lands in the review queue."""
    return PENDING


def review_notification(action: str, display_name: str, note: str | None) -> tuple[str, str]:
    """(title, body) in Persian for the creator when a manager decides."""
    titles = {
        "APPROVE": "درخواست شما تأیید شد",
        "REJECT": "درخواست شما رد شد",
        "REQUEST_EDIT": "درخواست شما نیازمند ویرایش یا تکمیل اطلاعات است",
        "REOPEN": "درخواست شما دوباره در صف بررسی قرار گرفت",
    }
    body = f"«{display_name}»"
    if note:
        body += f" — توضیح مدیر: {note}"
    return titles[action], body
