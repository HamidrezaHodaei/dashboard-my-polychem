"""
Notifications: creation helpers (called by other modules inside their own transaction),
the per-user list with lazily generated deadline warnings, and mark-as-read.

Deadline warnings (تسک نزدیک به موعد / سررسیدشده) are created when the user's list is
fetched -- the header polls it -- so they need no scheduler. All times are Tehran time.
"""
from datetime import datetime, time, timedelta, timezone

from app.extensions import db
from app.modules.notifications.models import Notification
from app.modules.tasks.models import Task, TaskAssignment, TaskStatus
from app.utils.jalali import TEHRAN, tehran_now

SOON_WINDOW = timedelta(hours=24)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def task_link(task: Task) -> str:
    return f"/tasks/project/{task.department_id}/task/{task.id}"


def notify(
    user_id: int, type_: str, title: str, body: str | None = None, *,
    link: str | None = None, task_id: int | None = None, dedupe_key: str | None = None,
) -> Notification | None:
    """Queue one notification for `user_id` (no commit -- the caller's transaction owns it).
    With a dedupe_key, a notification that already exists for that user is not repeated."""
    if dedupe_key and db.session.query(Notification.id).filter_by(user_id=user_id, dedupe_key=dedupe_key).first():
        return None
    row = Notification(
        user_id=user_id, type=type_, title=title[:200], body=(body or None) and body[:500],
        link=link, task_id=task_id, dedupe_key=dedupe_key,
    )
    db.session.add(row)
    return row


def _fa_digits(value) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _remaining_text(delta: timedelta) -> str:
    minutes = max(int(delta.total_seconds() // 60), 1)
    if minutes < 60:
        return f"{_fa_digits(minutes)} دقیقه"
    hours, rest = divmod(minutes, 60)
    return f"{_fa_digits(hours)} ساعت" + (f" و {_fa_digits(rest)} دقیقه" if rest else "")


def generate_deadline_notifications(user_id: int) -> int:
    """Warn about the user's open tasks that are due within 24 hours or already overdue.
    Each (task, due date) is warned about once per kind. Returns how many were created."""
    now = tehran_now()
    horizon = (now + SOON_WINDOW).date()
    rows = (
        db.session.query(Task)
        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
        .filter(
            TaskAssignment.assignee_user_id == user_id, TaskAssignment.unassigned_at.is_(None),
            Task.deleted_at.is_(None), Task.is_draft.is_(False), Task.is_archived.is_(False),
            Task.status.notin_([TaskStatus.DONE, TaskStatus.CANCELLED]),
            Task.due_date.isnot(None), Task.due_date <= horizon,
        )
        .all()
    )
    created = 0
    for task in rows:
        deadline = datetime.combine(task.due_date, task.due_time or time(23, 59), tzinfo=TEHRAN)
        if deadline <= now:
            made = notify(
                user_id, "TASK_OVERDUE", "سررسید تسک گذشته است",
                f"مهلت انجام تسک «{task.title}» به پایان رسیده است.",
                link=task_link(task), task_id=task.id, dedupe_key=f"overdue:{task.id}:{task.due_date}",
            )
        elif deadline - now <= SOON_WINDOW:
            made = notify(
                user_id, "TASK_DUE_SOON", "موعد تسک نزدیک است",
                f"فقط {_remaining_text(deadline - now)} تا مهلت تسک «{task.title}» باقی مانده است.",
                link=task_link(task), task_id=task.id, dedupe_key=f"soon:{task.id}:{task.due_date}",
            )
        else:
            continue
        created += 1 if made else 0
    if created:
        db.session.commit()
    return created


def _dump(n: Notification) -> dict:
    return {
        "id": n.id, "type": n.type, "title": n.title, "body": n.body, "link": n.link, "task_id": n.task_id,
        "is_read": n.read_at is not None,
        "created_at": (n.created_at if n.created_at.tzinfo else n.created_at.replace(tzinfo=timezone.utc)).isoformat(),
    }


def _accessible_task_ids(user_id: int, task_ids: set[int]) -> set[int]:
    """Of `task_ids`, the ones the user may still open (their unit / admin). A notification about
    a task that has since left the user's unit (e.g. after a transfer) must not leak its title."""
    if not task_ids:
        return set()
    from app.core.users.models import User  # local import: avoids a tasks <-> notifications cycle
    from app.modules.tasks.services import Authority

    user = db.session.get(User, user_id)
    if user is None:
        return set()
    auth = Authority(user)
    tasks = db.session.query(Task).filter(Task.id.in_(task_ids), Task.deleted_at.is_(None)).all()
    return {t.id for t in tasks if auth.in_units(t)}


def list_for(user_id: int, *, limit: int = 30, only_unread: bool = False, before_id: int | None = None) -> dict:
    """Newest first. `before_id` pages backwards (the "all notifications" page passes the id of
    the last item it already has); `has_more` tells the client whether another page exists."""
    try:
        generate_deadline_notifications(user_id)
    except Exception:  # a warning must never break the bell
        db.session.rollback()
    try:
        from app.modules.request_samples import reminders  # local import: request_samples imports this module

        reminders.generate_for(user_id)
    except Exception:  # same rule for the sample reminders
        db.session.rollback()
    try:
        from app.modules.customers import reminders as customer_reminders  # local import: avoids a cycle

        customer_reminders.generate_for(user_id)
    except Exception:  # same rule for the customer follow-up reminders
        db.session.rollback()
    query = db.session.query(Notification).filter(Notification.user_id == user_id)
    if only_unread:
        query = query.filter(Notification.read_at.is_(None))
    if before_id:
        query = query.filter(Notification.id < before_id)
    rows = query.order_by(Notification.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_before_id = rows[-1].id if rows else None  # cursor over the raw page, before access filtering
    allowed = _accessible_task_ids(user_id, {n.task_id for n in rows if n.task_id})
    items = [n for n in rows if n.task_id is None or n.task_id in allowed]
    unread = db.session.query(db.func.count(Notification.id)).filter(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    ).scalar()
    return {
        "items": [_dump(n) for n in items], "unread_count": int(unread or 0),
        "has_more": has_more, "next_before_id": next_before_id,
    }


def mark_read(user_id: int, *, ids: list[int] | None = None, all_: bool = False) -> int:
    query = db.session.query(Notification).filter(Notification.user_id == user_id, Notification.read_at.is_(None))
    if not all_:
        query = query.filter(Notification.id.in_(ids or [0]))
    count = query.update({Notification.read_at: _utcnow()}, synchronize_session=False)
    db.session.commit()
    return count
