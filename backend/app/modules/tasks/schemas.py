"""Pydantic schemas for /api/tasks -- SECURITY.md §4 / API.md §4."""
from datetime import date, datetime, time, timezone
from typing import Literal

from pydantic import field_validator, field_serializer, BaseModel, ConfigDict, Field

from app.modules.tasks.models import RuleAction, RuleSubject, RuleTarget, TaskPriority, TaskStatus


class RecurrenceIn(BaseModel):
    """Repeat rule. daily = DAY/1, weekly = WEEK/1, monthly = MONTH/1, yearly = YEAR/1;
    a manual span is any other interval (every 10 days, every 3 months, ...).
    MONTH and YEAR are Jalali."""

    unit: Literal["DAY", "WEEK", "MONTH", "YEAR"]
    interval: int = Field(default=1, ge=1, le=365)
    end_date: date | None = None


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    department_id: int
    team_id: int | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    due_date: date | None = None
    due_time: time | None = None  # Tehran time
    is_draft: bool = False
    progress: int = Field(default=0, ge=0, le=100)
    assignee_user_ids: list[int] = Field(default_factory=list)
    recurrence: RecurrenceIn | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    team_id: int | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    due_date: date | None = None
    due_time: time | None = None
    is_draft: bool | None = None
    is_archived: bool | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    recurrence: RecurrenceIn | None = None  # sent as null = stop repeating


class TaskAssign(BaseModel):
    assignee_user_id: int


class TaskAssigneesSet(BaseModel):
    """Replace the whole assignee list in one call (any number of people)."""

    assignee_user_ids: list[int] = Field(default_factory=list, max_length=100)


class TaskRefer(BaseModel):
    """An assignee hands the task on to someone else (hierarchical chain)."""

    to_user_id: int
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def _strip(cls, v):
        v = (v or "").strip()
        return v or None


class TaskAssignmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignee_user_id: int
    assigned_by_user_id: int
    assigned_at: datetime
    unassigned_at: datetime | None


class TaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    creator_id: int
    department_id: int
    team_id: int | None
    project_id: int | None
    priority: TaskPriority
    status: TaskStatus
    due_date: date | None
    due_time: time | None = None
    is_draft: bool
    is_archived: bool
    progress: int
    assignee_ids: list[int]
    recurrence: dict | None = None
    recurrence_source_id: int | None = None
    can_manage: bool = False  # set per caller by the route: may rename / delete this task and remove notes, checklist items
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    @field_serializer("completed_at")
    def _utc_opt(self, v: datetime | None):
        return None if v is None else (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).isoformat()

    @field_serializer("created_at", "updated_at")
    def _utc(self, v: datetime):
        # Timestamps are stored as naive UTC; say so explicitly so every client converts to
        # Tehran time correctly instead of reading them as local time.
        return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).isoformat()

    @field_serializer("due_time")
    def _hhmm(self, v: time | None):
        return v.strftime("%H:%M") if v else None


class TaskAnalytics(BaseModel):
    """Counts by status, within the actor's scope (AUTHORIZATION.md §7's
    `tasks.analytics.read`) -- deliberately minimal, no documented
    requirement specifies anything richer."""

    total: int
    by_status: dict[str, int]


class AssignmentRuleCreate(BaseModel):
    grantor_type: RuleSubject
    grantor_id: int
    target_type: RuleTarget
    target_id: int | None = None
    action: RuleAction = RuleAction.BOTH


class NoteCreate(BaseModel):
    """`body` may contain mention tokens `@[<user id>]`; they are resolved server-side."""

    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("body must not be blank")
        return v


class ChecklistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be blank")
        return v


class ChecklistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_done: bool | None = None
