"""
Task / TaskAssignment models — DATABASE.md "Task module tables".

Authorization for every task action resolves from `tasks.department_id`/
`tasks.team_id`/assignee membership — never from the acting user's own
`department_id` (AUTHORIZATION.md §8). This module defines storage only;
the actual checks live in app/modules/tasks/services.py via
app/permissions/*.
"""
import enum
from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import BigIntUnsigned, SoftDeleteMixin, TimestampMixin, _utcnow
from app.extensions import db


class TaskPriority(str, enum.Enum):
    """Not defined by any project document (DATABASE.md only says
    'priority ENUM') — these four values are a conventional, low-risk
    default rather than a documented business requirement."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, enum.Enum):
    """Same caveat as TaskPriority — DATABASE.md only says 'status ENUM'."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Task(TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_department_id", "department_id"),
        Index("ix_tasks_team_id", "team_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_recurrence_next_date", "recurrence_next_date"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    creator_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    department_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    # Reserved for a future Projects table (DATABASE.md: "project_id
    # (NULL, reserved)") — no Projects table exists yet, so no FK.
    project_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name="task_priority", native_enum=False, length=20),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status", native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.TODO,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Optional time of day of the deadline, in Tehran time (the date is a calendar date, not a UTC instant).
    due_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # -- recurring tasks (وظایف تکرارشونده) ---------------------------------
    # A task with `recurrence_unit` set is a SERIES TEMPLATE: every `recurrence_interval`
    # units (DAY / WEEK / MONTH / YEAR; months and years are Jalali) a fresh copy is created
    # (see recurrence.py). "Daily/weekly/monthly/yearly" are interval 1 of a unit; a manual
    # span is any interval, e.g. every 10 days or every 3 months.
    recurrence_unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    recurrence_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recurrence_next_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recurrence_anchor_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Jalali day-of-month the series started on
    # Set on the copies a series creates (points at the template task).
    recurrence_source_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    department: Mapped["Department"] = relationship("Department")
    team: Mapped["Team | None"] = relationship("Team")
    assignments: Mapped[list["TaskAssignment"]] = relationship(
        "TaskAssignment", back_populates="task", cascade="all, delete-orphan"
    )

    @property
    def assignee_ids(self) -> list[int]:
        return [a.assignee_user_id for a in self.assignments if a.unassigned_at is None]

    @property
    def recurrence(self) -> dict | None:
        if not self.recurrence_unit:
            return None
        return {
            "unit": self.recurrence_unit,
            "interval": self.recurrence_interval or 1,
            "end_date": self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            "next_date": self.recurrence_next_date.isoformat() if self.recurrence_next_date else None,
        }

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task id={self.id} title={self.title!r}>"


class TaskAssignment(db.Model):
    """
    DATABASE.md: "UNIQUE(task_id, assignee_user_id) where unassigned_at
    IS NULL (enforced at service layer)" — a partial-unique constraint
    isn't portable across MySQL/SQLite via a plain UniqueConstraint, so
    it is enforced in app/modules/tasks/services.py, not here. No
    created_at/updated_at/deleted_at, mirroring TeamMember's rationale:
    assignment rows are added/soft-unassigned (via unassigned_at), not
    audit-tracked the way entities are.
    """

    __tablename__ = "task_assignments"
    __table_args__ = (
        Index("ix_task_assignments_assignee_user_id", "assignee_user_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    assignee_user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by_user_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    # Referral chain (ارجاع سلسله‌مراتبی): when an assignee refers the task onward, the new
    # assignment points at the referrer's assignment, which is closed with end_reason=REFERRED.
    parent_assignment_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("task_assignments.id", ondelete="SET NULL"), nullable=True
    )
    end_reason: Mapped[str | None] = mapped_column(String(10), nullable=True)  # REMOVED | REFERRED
    referral_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="assignments")
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assignee_user_id])
    assigned_by: Mapped["User"] = relationship("User", foreign_keys=[assigned_by_user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaskAssignment task_id={self.task_id} assignee_user_id={self.assignee_user_id}>"


class RuleSubject(str, enum.Enum):
    USER = "USER"
    ROLE = "ROLE"


class RuleTarget(str, enum.Enum):
    ALL = "ALL"
    USER = "USER"
    ROLE = "ROLE"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"


class RuleAction(str, enum.Enum):
    """Which task action the rule grants: X -> Y -> CREATE (X may create
    tasks pre-assigned to Y), ASSIGN (X may assign existing tasks to Y),
    or BOTH."""

    CREATE = "CREATE"
    ASSIGN = "ASSIGN"
    BOTH = "BOTH"


class TaskAssignmentRule(TimestampMixin, db.Model):
    """
    "Who may define / assign tasks to whom". One row = the grantor (a
    user, or every holder of a role) may give tasks to the target (one
    user, every holder of a role, a department, a team, or everyone).
    Managed only by admins / holders of core.permission.update.
    """

    __tablename__ = "task_assignment_rules"
    __table_args__ = (
        Index("ix_task_assignment_rules_grantor", "grantor_type", "grantor_id"),
    )

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    grantor_type: Mapped[RuleSubject] = mapped_column(
        SAEnum(RuleSubject, name="task_rule_subject", native_enum=False, length=20), nullable=False
    )
    grantor_id: Mapped[int] = mapped_column(BigIntUnsigned, nullable=False)
    target_type: Mapped[RuleTarget] = mapped_column(
        SAEnum(RuleTarget, name="task_rule_target", native_enum=False, length=20), nullable=False
    )
    target_id: Mapped[int | None] = mapped_column(BigIntUnsigned, nullable=True)
    action: Mapped[RuleAction] = mapped_column(
        SAEnum(RuleAction, name="task_rule_action", native_enum=False, length=10),
        nullable=False, default=RuleAction.BOTH, server_default="BOTH",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class TaskNote(TimestampMixin, db.Model):
    """Internal (team-only) note attached to a task."""

    __tablename__ = "task_notes"
    __table_args__ = (Index("ix_task_notes_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Users @mentioned in `body` (tokens look like "@[12]"); derived server-side from the body.
    mentioned_user_ids: Mapped[list | None] = mapped_column(JSON(none_as_null=True), nullable=True)

    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])


class TaskChecklistItem(TimestampMixin, db.Model):
    """One checklist step of a task."""

    __tablename__ = "task_checklist_items"
    __table_args__ = (Index("ix_task_checklist_items_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(BigIntUnsigned, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskFile(TimestampMixin, db.Model):
    """File attached to a task. Any number per task; bytes live on disk under UPLOAD_DIR."""

    __tablename__ = "task_files"
    __table_args__ = (Index("ix_task_files_task_id", "task_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # random UUID; never the user's file name
    task_id: Mapped[int] = mapped_column(
        BigIntUnsigned, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntUnsigned, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by_user_id])
