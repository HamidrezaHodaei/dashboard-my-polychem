"""
Recurring tasks (وظایف تکرارشونده).

A task whose `recurrence_unit` is set is a series template. Every
`recurrence_interval` units a copy is created for the next occurrence:

    DAY    every N days
    WEEK   every N weeks (7 * N days)
    MONTH  every N Jalali months  (same Jalali day, clamped to the month's length)
    YEAR   every N Jalali years

Daily / weekly / monthly / yearly are interval 1 of a unit; "بازه دستی" is any
other interval (every 10 days, every 3 months, ...). All "today" decisions use
Tehran's calendar day.

Copies are created lazily by `generate_due_recurring_tasks()`, which is cheap
when nothing is due. It is called when tasks are listed and by
scripts/run_recurring_tasks.py (cron). The template row is "claimed" with a
compare-and-set UPDATE on `recurrence_next_date`, so two concurrent callers can
never both create the same occurrence.
"""
from datetime import date, timedelta

from app.core.audit_logs.services import write_audit_log
from app.extensions import db
from app.modules.notifications import services as notifications
from app.modules.tasks.models import Task, TaskAssignment, TaskChecklistItem, TaskStatus
from app.utils.jalali import add_jalali_months, add_jalali_years, tehran_today, to_jalali

UNITS = ("DAY", "WEEK", "MONTH", "YEAR")
MAX_INTERVAL = 365
MAX_CATCH_UP = 12  # occurrences created per template per run (a long outage must not flood)


def next_occurrence(after: date, unit: str, interval: int, anchor_day: int | None = None) -> date:
    """`anchor_day` = the Jalali day-of-month the series started on, so a clamp (31 -> 30)
    never drifts the series permanently to the shorter day."""
    if unit == "DAY":
        return after + timedelta(days=interval)
    if unit == "WEEK":
        return after + timedelta(weeks=interval)
    if unit == "MONTH":
        return add_jalali_months(after, interval, anchor_day)
    if unit == "YEAR":
        return add_jalali_years(after, interval, anchor_day)
    raise ValueError(f"Unknown recurrence unit {unit!r}")


def apply_recurrence(task: Task, recurrence: dict | None) -> None:
    """Sets / clears the series fields from a validated {unit, interval, end_date} dict.
    The template task itself is the first occurrence (its due date, or today if it has
    none); the first COPY is created one interval later."""
    if not recurrence:
        task.recurrence_unit = task.recurrence_interval = None
        task.recurrence_end_date = task.recurrence_next_date = task.recurrence_anchor_day = None
        return
    task.recurrence_unit = recurrence["unit"]
    task.recurrence_interval = recurrence["interval"]
    task.recurrence_end_date = recurrence.get("end_date")
    anchor = task.due_date or tehran_today()
    task.recurrence_anchor_day = to_jalali(anchor)[2]
    task.recurrence_next_date = next_occurrence(anchor, task.recurrence_unit, task.recurrence_interval, task.recurrence_anchor_day)


def _spawn_copy(template: Task, occurrence: date) -> Task:
    copy = Task(
        title=template.title, description=template.description, creator_id=template.creator_id,
        department_id=template.department_id, team_id=template.team_id, project_id=template.project_id,
        priority=template.priority, status=TaskStatus.TODO, due_date=occurrence, due_time=template.due_time,
        is_draft=False, is_archived=False, progress=0, recurrence_source_id=template.id,
    )
    db.session.add(copy)
    db.session.flush()
    for a in template.assignments:
        if a.unassigned_at is None:
            db.session.add(TaskAssignment(
                task_id=copy.id, assignee_user_id=a.assignee_user_id, assigned_by_user_id=template.creator_id,
            ))
    for a in template.assignments:
        if a.unassigned_at is None:
            notifications.notify(
                a.assignee_user_id, "TASK_ASSIGNED", "تسک تکرارشونده‌ی جدید",
                f"تسک «{copy.title}» برای موعد جدید ساخته شد.",
                link=notifications.task_link(copy), task_id=copy.id,
            )
    for i, item in enumerate(
        db.session.query(TaskChecklistItem).filter_by(task_id=template.id).order_by(TaskChecklistItem.position, TaskChecklistItem.id)
    ):
        db.session.add(TaskChecklistItem(task_id=copy.id, title=item.title, position=i + 1))  # unticked
    return copy


def generate_due_recurring_tasks(today: date | None = None) -> int:
    """Creates every occurrence that is due; returns how many tasks were created."""
    today = today or tehran_today()
    due = (
        db.session.query(Task.id)
        .filter(
            Task.deleted_at.is_(None), Task.recurrence_unit.isnot(None),
            Task.recurrence_next_date.isnot(None), Task.recurrence_next_date <= today,
            Task.is_draft.is_(False), Task.is_archived.is_(False),
            Task.status != TaskStatus.CANCELLED,
        )
        .all()
    )
    created = 0
    for (task_id,) in due:
        for _ in range(MAX_CATCH_UP):
            template = db.session.get(Task, task_id)
            if template is None or template.recurrence_next_date is None or template.recurrence_next_date > today:
                break
            occurrence = template.recurrence_next_date
            if template.recurrence_end_date and occurrence > template.recurrence_end_date:
                template.recurrence_next_date = None  # series finished
                db.session.commit()
                break
            following = next_occurrence(
                occurrence, template.recurrence_unit, template.recurrence_interval or 1, template.recurrence_anchor_day
            )
            claimed = (
                db.session.query(Task)
                .filter(Task.id == task_id, Task.recurrence_next_date == occurrence)
                .update({Task.recurrence_next_date: following}, synchronize_session=False)
            )
            if not claimed:  # another worker took this occurrence
                db.session.rollback()
                break
            copy = _spawn_copy(template, occurrence)
            write_audit_log(
                user_id=None, action="recurrence_create", module="tasks", entity_type="task", entity_id=copy.id,
                metadata={"source_task_id": template.id, "occurrence": occurrence.isoformat()}, ip_address=None,
            )
            db.session.commit()
            db.session.expire_all()
            created += 1
    return created
