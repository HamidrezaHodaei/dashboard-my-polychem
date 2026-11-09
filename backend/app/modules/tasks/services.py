"""
Service layer for /api/tasks -- Phase 4a.

Same pattern established by Phase 4's core CRUD modules (see
app/core/departments/services.py): permission checks live here, not in
routes.py, because CREATE needs scope info from the parsed body and LIST
needs to filter by the union of covering grants rather than allow/deny a
single target.

AUTHORIZATION.md §8: task authorization is ALWAYS resolved from the
task's own department_id/team_id/assignees -- never from the acting
user's own placement. `_task_target_scope()` below is the one place that
resolves "what scope does this task live at" (TEAM if it has a team,
else DEPARTMENT), and every permission check in this module goes through
it (or the equivalent payload-derived resolution for CREATE).
"""
import logging
import re
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import ScopeType
from app.core.departments.models import Department
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.extensions import db
from app.modules.notifications import services as notifications
from app.modules.tasks import files as task_files
from app.modules.tasks import recurrence
from app.modules.tasks import rules as task_rules
from app.modules.tasks.models import RuleAction
from app.modules.tasks.models import (
    Task,
    TaskAssignment,
    TaskChecklistItem,
    TaskFile,
    TaskNote,
    TaskStatus,
)
from app.modules.tasks.schemas import (
    ChecklistCreate,
    ChecklistUpdate,
    NoteCreate,
    TaskAssigneesSet,
    TaskCreate,
    TaskRefer,
    TaskUpdate,
)
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import get_effective_grants as get_matching_grants_all
from app.permissions.service import get_matching_grants, has_permission, is_admin
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "tasks"
ENTITY_TYPE = "task"
log = logging.getLogger(__name__)


def _iso_utc(dt: datetime | None) -> str | None:
    """Stored timestamps are naive UTC -- always send them with an explicit offset."""
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


# ====================================================================
# «مدیر» (manager) + unit isolation
# ====================================================================
class Authority:
    """Answers, for ONE actor and many tasks, the two questions this module keeps asking.

    * is_manager(task): may the actor rename / delete the task and delete its notes,
      checklist items? A manager is an admin or a holder of `tasks.task.delete` at the
      task's scope -- i.e. it is granted through the normal role / permission matrix
      (AUTHORIZATION.md forbids reading departments.manager_user_id for this) -- AND the
      task is inside the actor's own unit (admins excepted).
    * in_units(task): is the task inside the actor's own department / teams?

    UNIT ISOLATION (hard rule, enforced server-side for every task endpoint):
      - Only a user holding the active `admin` role sees / manages every unit.
      - Everybody else is confined to their own unit: `users.department_id` plus the
        departments of the teams they are a member of. Permissions (Create / Read / Edit /
        Delete) are evaluated *inside* that unit -- a role or user grant can narrow access
        further, but it can never widen it beyond the unit, not even a GLOBAL grant
        (the permission matrix writes GLOBAL grants, so this clamp is what keeps an
        "Edit" holder from touching other departments).
      - Having created a task, or being (or having been) assigned to it, does NOT grant
        access once the task is outside the user's unit (e.g. after a transfer).
    """

    def __init__(self, actor: User):
        self.actor = actor
        self.is_admin = is_admin(actor)
        self.sees_all = self.is_admin
        self._manager_cache: dict = {}
        self._depts: set[int] | None = None
        self._assigned: set[int] | None = None

    # -- units ------------------------------------------------------
    @property
    def own_department_ids(self) -> set[int]:
        if self._depts is None:
            ids = {self.actor.department_id} if self.actor.department_id else set()
            rows = (
                db.session.query(Team.department_id)
                .join(TeamMember, TeamMember.team_id == Team.id)
                .filter(TeamMember.user_id == self.actor.id, Team.deleted_at.is_(None))
            )
            ids |= {r[0] for r in rows}
            self._depts = ids
        return self._depts

    @property
    def assigned_task_ids(self) -> set[int]:
        if self._assigned is None:
            rows = db.session.query(TaskAssignment.task_id).filter(
                TaskAssignment.assignee_user_id == self.actor.id, TaskAssignment.unassigned_at.is_(None)
            )
            self._assigned = {r[0] for r in rows}
        return self._assigned

    def in_units(self, task: Task) -> bool:
        return self.sees_all or task.department_id in self.own_department_ids

    def department_visible(self, department_id: int) -> bool:
        return self.sees_all or department_id in self.own_department_ids

    # -- manager ----------------------------------------------------
    def is_manager(self, task: Task) -> bool:
        if self.is_admin:
            return True
        if not self.in_units(task):
            return False
        key = (task.department_id, task.team_id)
        if key not in self._manager_cache:
            scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
            self._manager_cache[key] = has_permission(self.actor, "tasks.task.delete", scope_type, scope_id)
        return self._manager_cache[key]


def _notify_assigned(task: Task, user_ids, actor: User, kind: str = "TASK_ASSIGNED", note: str | None = None) -> None:
    """Tell people a task landed on them (never the person who did it). Part of the caller's transaction."""
    for uid in dict.fromkeys(user_ids):
        if uid == actor.id:
            continue
        if kind == "TASK_REFERRED":
            title, body = "تسکی به شما ارجاع شد", f"{actor.full_name} تسک «{task.title}» را به شما ارجاع داد."
            if note:
                body += f" توضیح: {note}"
        else:
            title, body = "تسک جدید برای شما", f"تسک «{task.title}» توسط {actor.full_name} به شما واگذار شد."
        notifications.notify(uid, kind, title, body, link=notifications.task_link(task), task_id=task.id)


def _assert_in_units(auth: Authority, task: Task) -> None:
    if not auth.in_units(task):
        raise PermissionDeniedError(
            "permission_denied", "This task belongs to another department or unit."
        )


def _assert_manager(auth: Authority, task: Task, what: str) -> None:
    if not auth.is_manager(task):
        raise PermissionDeniedError("permission_denied", f"Only a manager can {what}.")


def _require(actor: User, action: str, scope_type, scope_id) -> None:
    key = f"tasks.task.{action}"
    if not has_permission(actor, key, scope_type, scope_id):
        raise PermissionDeniedError(
            "permission_denied", f"Missing permission '{key}' for this action."
        )


def _task_target_scope(department_id: int, team_id: int | None):
    """AUTHORIZATION.md §7's worked example: a TEAM-scoped grant covers
    only that team; a DEPARTMENT-scoped grant covers the whole
    department (every team under it). Resolving the target as TEAM
    (when the task has one) rather than always DEPARTMENT is what makes
    both grant shapes work correctly via the existing scope_covers
    hierarchy -- a department-level grant still covers a team-level
    target, but not vice versa."""
    if team_id is not None:
        return ScopeType.TEAM, team_id
    return ScopeType.DEPARTMENT, department_id


def _get_or_404(task_id: int) -> Task:
    task = db.session.get(Task, task_id)
    if task is None or task.deleted_at is not None:
        raise NotFoundError(f"Task {task_id} was not found.")
    return task


def _get_department_or_404(department_id: int) -> Department:
    dept = db.session.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise NotFoundError(f"Department {department_id} was not found.")
    return dept


def _get_team_or_404(team_id: int) -> Team:
    team = db.session.get(Team, team_id)
    if team is None or team.deleted_at is not None:
        raise NotFoundError(f"Team {team_id} was not found.")
    return team


def _load_assignee(assignee_user_id: int) -> User:
    assignee = db.session.get(User, assignee_user_id)
    if assignee is None or assignee.deleted_at is not None:
        raise NotFoundError(f"User {assignee_user_id} was not found.")
    return assignee


def _check_assignee_belongs(assignee: User, department_id: int, team_id: int | None) -> None:
    """AUTHORIZATION.md §5/§8 step 3: the assignee must belong to the task's
    own team (if it has one) or department (if it doesn't)."""
    if team_id is not None:
        is_member = (
            db.session.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.user_id == assignee.id)
            .first()
            is not None
        )
        if not is_member:
            raise ConflictError("Assignee is not a member of this task's team.")
    elif assignee.department_id != department_id:
        raise ConflictError("Assignee does not belong to this task's department.")


def _authorize_assignee(actor: User, assignee: User, scope_type, scope_id, department_id, team_id,
                        matcher=None, action: RuleAction = RuleAction.ASSIGN) -> None:
    """Permission + organizational membership + 'who may create-for /
    assign-to whom' rule (action distinguishes the two for the
    X -> Y -> Create/Assign Task relationship)."""
    if assignee.id == actor.id:
        # Self-assignment: no rule needed, but the actor must be able to
        # work on the task at this scope.
        if not (has_permission(actor, "tasks.task.assign", scope_type, scope_id)
                or has_permission(actor, "tasks.task.update", scope_type, scope_id)
                or has_permission(actor, "tasks.task.create", scope_type, scope_id)):
            raise PermissionDeniedError(
                "permission_denied", "Missing permission 'tasks.task.assign' for this action."
            )
        return
    _require(actor, "assign", scope_type, scope_id)
    _check_assignee_belongs(assignee, department_id, team_id)
    task_rules.assert_can_assign_to(actor, assignee, matcher, action=action)


# Status transitions available to a user who is ASSIGNED to the task.
# "Request Completion Approval" is the REVIEW status. An assignee can never
# move a task to DONE or CANCELLED themselves. Who may approve / complete is
# intentionally not defined here (no new permission rules).
ASSIGNEE_ALLOWED_STATUSES = frozenset({TaskStatus.REVIEW})


def _assert_assignee_status_allowed(actor: User, assigned_ids, current, new) -> None:
    """Raise if `actor` is assigned to the task and `new` is not a status an
    assignee may set. Setting the status it already has is a no-op."""
    if actor.id not in assigned_ids or new == current:
        return
    if is_admin(actor):
        return
    if new not in ASSIGNEE_ALLOWED_STATUSES:
        raise PermissionDeniedError(
            "permission_denied",
            "As the assignee you can only change the status to 'Request Completion Approval'. "
            "You cannot set a task to Completed or Cancelled yourself.",
        )


def _scope_filtered_task_query(actor: User, permission_key: str):
    """Grant-based scope (below) INTERSECTED with unit isolation: unless the actor is an
    admin, only tasks of their own department / teams are ever returned -- whatever the
    scope of their grants (a GLOBAL grant is clamped to the user's unit) and whether or
    not they created the task or are assigned to it."""
    query = _grant_scoped_task_query(actor, permission_key)
    auth = Authority(actor)
    if auth.sees_all:
        return query
    if not auth.own_department_ids:
        return query.filter(db.false())
    return query.filter(Task.department_id.in_(auth.own_department_ids))


def _grant_scoped_task_query(actor: User, permission_key: str):
    """Builds the base Task query filtered to every scope the actor
    holds `permission_key` at (GLOBAL / ORGANIZATION / DEPARTMENT /
    TEAM / SELF), per AUTHORIZATION.md §5's "list needs the union of
    covering grants" resolution. Shared by list_tasks (tasks.task.read)
    and task_analytics (tasks.analytics.read) so the same scope logic
    isn't duplicated for two different permission keys."""
    query = db.session.query(Task).filter(Task.deleted_at.is_(None))

    grants = get_matching_grants(actor, permission_key)
    if any(g.scope_type == ScopeType.GLOBAL for g in grants):
        return query

    org_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}
    dept_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.DEPARTMENT}
    team_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.TEAM}
    has_self = any(g.scope_type == ScopeType.SELF for g in grants)

    conditions = []
    if org_ids:
        org_dept_ids = [
            row.id
            for row in db.session.query(Department.id).filter(
                Department.organization_id.in_(org_ids)
            )
        ]
        if org_dept_ids:
            conditions.append(Task.department_id.in_(org_dept_ids))
    if dept_ids:
        conditions.append(Task.department_id.in_(dept_ids))
    if team_ids:
        conditions.append(Task.team_id.in_(team_ids))
    if has_self:
        assigned_task_ids = db.session.query(TaskAssignment.task_id).filter(
            TaskAssignment.assignee_user_id == actor.id,
            TaskAssignment.unassigned_at.is_(None),
        )
        conditions.append(db.or_(Task.creator_id == actor.id, Task.id.in_(assigned_task_ids)))

    if conditions:
        return query.filter(db.or_(*conditions))
    return query.filter(db.false())


def list_tasks(
    actor: User, *, page: int, per_page: int, status: TaskStatus | None = None
):
    _require(actor, "read", None, None)
    _run_recurrence_safely()

    query = _scope_filtered_task_query(actor, "tasks.task.read")
    if status is not None:
        query = query.filter(Task.status == status)

    query = query.order_by(Task.id)
    return paginate_query(query, page, per_page)


def _run_recurrence_safely() -> None:
    """Create any recurring-task occurrence that has come due (cheap when none has).
    A failure here must never break listing tasks."""
    try:
        recurrence.generate_due_recurring_tasks()
    except Exception:  # pragma: no cover - defensive
        db.session.rollback()
        log.exception("Could not generate recurring tasks")


def get_task(actor: User, task_id: int) -> Task:
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    _assert_in_units(Authority(actor), task)
    _require(actor, "read", scope_type, scope_id)
    return task


def create_task(actor: User, payload: TaskCreate, *, ip_address: str | None) -> Task:
    if not Authority(actor).department_visible(payload.department_id):
        raise PermissionDeniedError("permission_denied", "You can only create tasks in your own department.")
    _get_department_or_404(payload.department_id)
    if payload.team_id is not None:
        team = _get_team_or_404(payload.team_id)
        if team.department_id != payload.department_id:
            raise ConflictError("team_id does not belong to the given department_id.")

    scope_type, scope_id = _task_target_scope(payload.department_id, payload.team_id)
    _require(actor, "create", scope_type, scope_id)

    # Validate every requested assignee BEFORE anything is written.
    assignees: list[User] = []
    matcher = task_rules.RuleMatcher(actor)
    for uid in dict.fromkeys(payload.assignee_user_ids):
        assignee = _load_assignee(uid)
        _authorize_assignee(actor, assignee, scope_type, scope_id,
                            payload.department_id, payload.team_id, matcher,
                            action=RuleAction.CREATE)
        assignees.append(assignee)

    _assert_assignee_status_allowed(
        actor, {a.id for a in assignees}, TaskStatus.TODO, payload.status
    )

    task = Task(
        title=payload.title,
        description=payload.description,
        creator_id=actor.id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        priority=payload.priority,
        status=payload.status,
        due_date=payload.due_date,
        due_time=payload.due_time,
        is_draft=payload.is_draft,
        progress=payload.progress,
    )
    if payload.recurrence is not None:
        recurrence.apply_recurrence(task, payload.recurrence.model_dump())
    db.session.add(task)
    try:
        db.session.flush()
        for assignee in assignees:
            db.session.add(TaskAssignment(
                task_id=task.id, assignee_user_id=assignee.id, assigned_by_user_id=actor.id
            ))
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not create task (constraint violation).") from exc

    _notify_assigned(task, [a.id for a in assignees], actor)
    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id,
        metadata={"title": task.title, "department_id": task.department_id, "team_id": task.team_id,
                  "assignee_user_ids": [a.id for a in assignees]},
        ip_address=ip_address,
    )
    db.session.commit()
    return task


def update_task(actor: User, task_id: int, payload: TaskUpdate, *, ip_address: str | None) -> Task:
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    auth = Authority(actor)
    _assert_in_units(auth, task)

    changes = payload.model_dump(exclude_unset=True)
    # A title is fixed once the task exists: only a manager may change it (re-sending the
    # same title, as the edit form does, is not a change).
    if "title" in changes:
        if changes["title"] == task.title:
            changes.pop("title")
        else:
            _assert_manager(auth, task, "change a task's title")

    # An assignee may always ask for completion approval on their own task,
    # even without `tasks.task.update` -- but nothing else in that case.
    approval_request_only = (
        actor.id in task.assignee_ids
        and changes.get("status") == TaskStatus.REVIEW
        and set(changes) <= {"status", "progress"}
    )
    if not approval_request_only:
        _require(actor, "update", scope_type, scope_id)
    if "status" in changes:
        if changes["status"] is None:
            changes.pop("status")
        else:
            _assert_assignee_status_allowed(
                actor, set(task.assignee_ids), task.status, changes["status"]
            )
    if "team_id" in changes and changes["team_id"] is not None:
        team = _get_team_or_404(changes["team_id"])
        if team.department_id != task.department_id:
            raise ConflictError("team_id does not belong to this task's department.")

    recurrence_change = "recurrence" in changes
    new_rule = changes.pop("recurrence", None)
    for field, value in changes.items():
        setattr(task, field, value)
    if recurrence_change:
        recurrence.apply_recurrence(task, new_rule)
    elif task.recurrence_unit and "due_date" in changes:
        # the series is anchored on the due date: re-anchor it
        recurrence.apply_recurrence(task, {
            "unit": task.recurrence_unit, "interval": task.recurrence_interval or 1,
            "end_date": task.recurrence_end_date,
        })
    if recurrence_change:
        changes["recurrence"] = new_rule

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update task (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return task


def delete_task(actor: User, task_id: int, *, ip_address: str | None) -> None:
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    auth = Authority(actor)
    _assert_in_units(auth, task)
    _require(actor, "delete", scope_type, scope_id)
    _assert_manager(auth, task, "delete a task")

    task.deleted_at = datetime.now(timezone.utc)

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, ip_address=ip_address,
    )
    db.session.commit()


def assign_task(actor: User, task_id: int, assignee_user_id: int, *, ip_address: str | None) -> TaskAssignment:
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    _assert_in_units(Authority(actor), task)
    assignee = _load_assignee(assignee_user_id)

    if assignee.id != actor.id:
        _require(actor, "assign", scope_type, scope_id)
        _check_assignee_belongs(assignee, task.department_id, task.team_id)
        task_rules.assert_can_assign_to(actor, assignee, action=RuleAction.ASSIGN)
    else:
        _authorize_assignee(actor, assignee, scope_type, scope_id, task.department_id, task.team_id,
                            action=RuleAction.ASSIGN)

    existing = (
        db.session.query(TaskAssignment)
        .filter(
            TaskAssignment.task_id == task.id,
            TaskAssignment.assignee_user_id == assignee_user_id,
            TaskAssignment.unassigned_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("This user is already assigned to this task.")

    assignment = TaskAssignment(
        task_id=task.id, assignee_user_id=assignee_user_id, assigned_by_user_id=actor.id
    )
    db.session.add(assignment)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not create assignment (constraint violation).") from exc

    _notify_assigned(task, [assignee.id], actor)
    write_audit_log(
        user_id=actor.id, action="assign", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"assignee_user_id": assignee_user_id}, ip_address=ip_address,
    )
    db.session.commit()
    return assignment


def unassign_task(actor: User, task_id: int, assignee_user_id: int, *, ip_address: str | None) -> None:
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    _assert_in_units(Authority(actor), task)
    # Reuses tasks.task.assign -- no separate "unassign" permission key
    # is documented anywhere, and assigning/removing an assignment are
    # the same managerial action.
    _require(actor, "assign", scope_type, scope_id)

    assignment = (
        db.session.query(TaskAssignment)
        .filter(
            TaskAssignment.task_id == task.id,
            TaskAssignment.assignee_user_id == assignee_user_id,
            TaskAssignment.unassigned_at.is_(None),
        )
        .first()
    )
    if assignment is None:
        raise NotFoundError("Active assignment was not found.")

    assignment.unassigned_at = datetime.now(timezone.utc)
    assignment.end_reason = "REMOVED"

    write_audit_log(
        user_id=actor.id, action="unassign", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"assignee_user_id": assignee_user_id}, ip_address=ip_address,
    )
    db.session.commit()


def task_analytics(actor: User) -> dict:
    """Counts by status, within the actor's scope -- AUTHORIZATION.md §7's
    `tasks.analytics.read`. Deliberately minimal, since no document
    specifies anything richer."""
    if not has_permission(actor, "tasks.analytics.read"):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'tasks.analytics.read' for this action."
        )

    query = _scope_filtered_task_query(actor, "tasks.analytics.read")
    items = query.all()
    by_status: dict[str, int] = {}
    for task in items:
        key = task.status.value if hasattr(task.status, "value") else str(task.status)
        by_status[key] = by_status.get(key, 0) + 1
    return {"total": len(items), "by_status": by_status}


def task_meta(actor: User) -> dict:
    """Everything the Tasks UI needs in ONE call, derived from the actor's
    own permissions (so ordinary employees need no core.* read access)."""
    from app.permissions.registry import REGISTRY

    task_keys = [k for k in REGISTRY if k.startswith("tasks.")]
    held = {g.permission_key for g in get_matching_grants_all(actor)}
    if not any(k in held for k in task_keys):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'tasks.task.read' for this action."
        )

    _run_recurrence_safely()
    # Unit isolation: an ordinary user's "projects" (departments), teams and people are only
    # those of their own unit. Only admins see every unit.
    auth = Authority(actor)
    visible_dept_ids = None if auth.sees_all else set(auth.own_department_ids)
    dept_query = db.session.query(Department).filter(Department.deleted_at.is_(None), Department.is_active.is_(True))
    team_query = db.session.query(Team).filter(Team.deleted_at.is_(None))
    if visible_dept_ids is not None:
        dept_query = dept_query.filter(Department.id.in_(visible_dept_ids)) if visible_dept_ids else dept_query.filter(db.false())
        team_query = team_query.filter(Team.department_id.in_(visible_dept_ids)) if visible_dept_ids else team_query.filter(db.false())
    departments = dept_query.order_by(Department.name).all()
    teams = team_query.order_by(Team.name).all()
    # "Who may I create a task for" and "who may I (re)assign an existing
    # task to" can differ now that rules carry an action (CREATE/ASSIGN/
    # BOTH) -- the Tasks UI picks the right list for the dialog it shows.
    def _dump_users(users):
        return [
            {"id": u.id, "full_name": u.full_name, "email": u.email, "department_id": u.department_id}
            for u in users
            if visible_dept_ids is None or u.department_id in visible_dept_ids or u.id == actor.id
        ]
    create_users = task_rules.assignable_users(actor, action=RuleAction.CREATE)
    assign_users = task_rules.assignable_users(actor, action=RuleAction.ASSIGN)
    return {
        "me": {"id": actor.id, "full_name": actor.full_name, "department_id": actor.department_id},
        "departments": [
            {"id": d.id, "name": d.name, "organization_id": d.organization_id} for d in departments
        ],
        "teams": [{"id": t.id, "name": t.name, "department_id": t.department_id} for t in teams],
        "assignable_users": _dump_users(create_users),
        "assignable_users_create": _dump_users(create_users),
        "assignable_users_assign": _dump_users(assign_users),
        "permissions": {
            "create": "tasks.task.create" in held,
            "update": "tasks.task.update" in held,
            "delete": "tasks.task.delete" in held,
            "assign": "tasks.task.assign" in held,
            "analytics": "tasks.analytics.read" in held,
            # «مدیر»: may rename / delete tasks, delete messages, checklist items and others' files
            "manage": is_admin(actor) or "tasks.task.delete" in held,
        },
        "can_manage_rules": task_rules.can_manage_rules(actor),
        "is_admin": is_admin(actor),
    }


# ====================================================================
# Internal notes + checklist
# ====================================================================
def _is_assignee(actor: User, task: Task) -> bool:
    return actor.id in task.assignee_ids


def _can_view_task(actor: User, task: Task, auth: Authority | None = None) -> bool:
    """Notes, checklist, files, assignment history and every other sub-resource of a task
    follow this one rule: the task must be inside the actor's unit (admins: always) AND the
    actor is its assignee / creator or holds `tasks.task.read` at the task's scope."""
    auth = auth or Authority(actor)
    if not auth.in_units(task):
        return False
    if _is_assignee(actor, task) or task.creator_id == actor.id:
        return True
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    return has_permission(actor, "tasks.task.read", scope_type, scope_id)


def _can_manage_task(actor: User, task: Task) -> bool:
    """Edit/remove checklist items, remove other people's notes."""
    auth = Authority(actor)
    if auth.is_admin:
        return True
    if not auth.in_units(task):
        return False
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    return task.creator_id == actor.id or has_permission(actor, "tasks.task.update", scope_type, scope_id)


def _viewable_task_or_403(actor: User, task_id: int) -> Task:
    task = _get_or_404(task_id)
    if not _can_view_task(actor, task):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'tasks.task.read' for this action."
        )
    return task


_MENTION_RE = re.compile(r"@\[(\d+)\]")


def _mention_ids(body: str) -> list[int]:
    return list(dict.fromkeys(int(m) for m in _MENTION_RE.findall(body)))


def _names_for(ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.session.query(User.id, User.full_name).filter(User.id.in_(ids)).all()
    return {r[0]: r[1] for r in rows}


def _dump_note(n: TaskNote, names: dict[int, str] | None = None) -> dict:
    ids = list(n.mentioned_user_ids or [])
    names = names if names is not None else _names_for(set(ids))
    return {
        "id": n.id,
        "task_id": n.task_id,
        "author_id": n.author_id,
        "author_name": n.author.full_name if n.author else "Deleted user",
        "body": n.body,
        "mentions": [{"id": i, "full_name": names.get(i, "Deleted user")} for i in ids],
        "created_at": _iso_utc(n.created_at),
    }


def _user_can_see_task(user: User, task: Task) -> bool:
    """May `user` open this task? (used to validate @mentions -- nobody can be pulled
    into a task they could not read).  Mirrors the Authority rules for a single user."""
    if user.deleted_at is not None or not user.is_active:
        return False
    if is_admin(user):
        return True
    if user.department_id == task.department_id:
        return True
    return db.session.query(TeamMember).join(Team, Team.id == TeamMember.team_id).filter(
        TeamMember.user_id == user.id, Team.department_id == task.department_id, Team.deleted_at.is_(None)
    ).first() is not None


def mention_candidates(actor: User, task_id: int) -> list[dict]:
    """People that can be @mentioned in this task's notes."""
    task = _viewable_task_or_403(actor, task_id)
    users: dict[int, User] = {}
    for u in db.session.query(User).filter(
        User.department_id == task.department_id, User.deleted_at.is_(None), User.is_active.is_(True)
    ):
        users[u.id] = u
    extra_ids = set(task.assignee_ids) | {task.creator_id}
    if task.team_id is not None:
        extra_ids |= {r[0] for r in db.session.query(TeamMember.user_id).filter_by(team_id=task.team_id)}
    for u in db.session.query(User).filter(User.id.in_(extra_ids - set(users)), User.deleted_at.is_(None)):
        if u.is_active and _user_can_see_task(u, task):
            users[u.id] = u
    return [{"id": u.id, "full_name": u.full_name} for u in sorted(users.values(), key=lambda x: x.full_name)]


def list_notes(actor: User, task_id: int) -> list[dict]:
    task = _viewable_task_or_403(actor, task_id)
    rows = (
        db.session.query(TaskNote)
        .filter(TaskNote.task_id == task.id)
        .order_by(TaskNote.id.desc())
        .all()
    )
    names = _names_for({i for n in rows for i in (n.mentioned_user_ids or [])})
    return [_dump_note(n, names) for n in rows]


def add_note(actor: User, task_id: int, payload: NoteCreate, *, ip_address: str | None) -> dict:
    task = _viewable_task_or_403(actor, task_id)
    mention_ids = _mention_ids(payload.body)
    if mention_ids:
        found = {u.id: u for u in db.session.query(User).filter(User.id.in_(mention_ids))}
        for uid in mention_ids:
            user = found.get(uid)
            if user is None or not _user_can_see_task(user, task):
                raise ConflictError(f"User {uid} cannot be mentioned: they have no access to this task.")
    note = TaskNote(task_id=task.id, author_id=actor.id, body=payload.body, mentioned_user_ids=mention_ids or None)
    db.session.add(note)
    db.session.flush()
    for uid in mention_ids:
        if uid != actor.id:
            notifications.notify(
                uid, "TASK_MENTION", "شما در یک تسک منشن شدید",
                f"{actor.full_name} در تسک «{task.title}» شما را منشن کرد.",
                link=notifications.task_link(task), task_id=task.id,
            )
    write_audit_log(
        user_id=actor.id, action="note_add", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"note_id": note.id, "mentioned_user_ids": mention_ids}, ip_address=ip_address,
    )
    db.session.commit()
    return _dump_note(note)


def delete_note(actor: User, task_id: int, note_id: int, *, ip_address: str | None) -> None:
    task = _viewable_task_or_403(actor, task_id)
    note = db.session.get(TaskNote, note_id)
    if note is None or note.task_id != task.id:
        raise NotFoundError(f"Note {note_id} was not found.")
    # Messages are part of the task's record: only a manager may remove one (not even its author).
    _assert_manager(Authority(actor), task, "delete a task message")
    db.session.delete(note)
    write_audit_log(
        user_id=actor.id, action="note_delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"note_id": note_id}, ip_address=ip_address,
    )
    db.session.commit()


def my_mentions(actor: User, limit: int = 50) -> list[dict]:
    """Notes that @mention the actor, newest first (only on tasks they can still open)."""
    out: list[dict] = []
    auth = Authority(actor)
    rows = (
        db.session.query(TaskNote).filter(TaskNote.mentioned_user_ids.isnot(None))
        .order_by(TaskNote.id.desc()).limit(500).all()
    )
    for n in rows:
        if actor.id not in (n.mentioned_user_ids or []):
            continue
        task = db.session.get(Task, n.task_id)
        if task is None or task.deleted_at is not None or not _can_view_task(actor, task, auth):
            continue
        item = _dump_note(n)
        item["task_title"] = task.title
        item["department_id"] = task.department_id
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _dump_item(i: TaskChecklistItem) -> dict:
    return {
        "id": i.id,
        "task_id": i.task_id,
        "title": i.title,
        "is_done": i.is_done,
        "position": i.position,
        "completed_by_user_id": i.completed_by_user_id,
        "completed_at": i.completed_at.isoformat() if i.completed_at else None,
    }


def _get_item_or_404(task: Task, item_id: int) -> TaskChecklistItem:
    item = db.session.get(TaskChecklistItem, item_id)
    if item is None or item.task_id != task.id:
        raise NotFoundError(f"Checklist item {item_id} was not found.")
    return item


def list_checklist(actor: User, task_id: int) -> list[dict]:
    task = _viewable_task_or_403(actor, task_id)
    rows = (
        db.session.query(TaskChecklistItem)
        .filter(TaskChecklistItem.task_id == task.id)
        .order_by(TaskChecklistItem.position, TaskChecklistItem.id)
        .all()
    )
    return [_dump_item(i) for i in rows]


def add_checklist_item(actor: User, task_id: int, payload: ChecklistCreate, *, ip_address: str | None) -> dict:
    task = _viewable_task_or_403(actor, task_id)
    # assignees may add steps to their own work; everyone else needs manage rights
    if not (_is_assignee(actor, task) or _can_manage_task(actor, task)):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'tasks.task.update' for this action."
        )
    last = (
        db.session.query(db.func.max(TaskChecklistItem.position))
        .filter(TaskChecklistItem.task_id == task.id)
        .scalar()
    )
    item = TaskChecklistItem(task_id=task.id, title=payload.title, position=(last or 0) + 1)
    db.session.add(item)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="checklist_add", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"item_id": item.id}, ip_address=ip_address,
    )
    db.session.commit()
    return _dump_item(item)


def update_checklist_item(actor: User, task_id: int, item_id: int, payload: ChecklistUpdate,
                          *, ip_address: str | None) -> dict:
    task = _viewable_task_or_403(actor, task_id)
    item = _get_item_or_404(task, item_id)
    changes = payload.model_dump(exclude_unset=True)

    can_toggle = _is_assignee(actor, task) or _can_manage_task(actor, task)
    if "title" in changes and changes["title"] is not None:
        if not _can_manage_task(actor, task):
            raise PermissionDeniedError(
                "permission_denied", "Missing permission 'tasks.task.update' for this action."
            )
        item.title = changes["title"]
    if "is_done" in changes and changes["is_done"] is not None:
        if not can_toggle:
            raise PermissionDeniedError(
                "permission_denied", "Only an assignee or a task manager can tick checklist items."
            )
        if changes["is_done"] != item.is_done:
            item.is_done = changes["is_done"]
            item.completed_by_user_id = actor.id if item.is_done else None
            item.completed_at = datetime.now(timezone.utc).replace(tzinfo=None) if item.is_done else None

    write_audit_log(
        user_id=actor.id, action="checklist_update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"item_id": item.id, "changed_fields": list(changes.keys())},
        ip_address=ip_address,
    )
    db.session.commit()
    return _dump_item(item)


def delete_checklist_item(actor: User, task_id: int, item_id: int, *, ip_address: str | None) -> None:
    task = _viewable_task_or_403(actor, task_id)
    item = _get_item_or_404(task, item_id)
    _assert_manager(Authority(actor), task, "delete a checklist item")
    db.session.delete(item)
    write_audit_log(
        user_id=actor.id, action="checklist_delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=task.id, metadata={"item_id": item_id}, ip_address=ip_address,
    )
    db.session.commit()


# ====================================================================
# Many assignees at once, hierarchical referral, assignment history
# ====================================================================
def set_assignees(actor: User, task_id: int, payload: TaskAssigneesSet, *, ip_address: str | None) -> Task:
    """Make the task's assignee list exactly `assignee_user_ids` (any number of people)."""
    task = _get_or_404(task_id)
    scope_type, scope_id = _task_target_scope(task.department_id, task.team_id)
    _assert_in_units(Authority(actor), task)

    wanted = list(dict.fromkeys(payload.assignee_user_ids))
    current = set(task.assignee_ids)
    to_add = [uid for uid in wanted if uid not in current]
    to_remove = [uid for uid in current if uid not in wanted]

    matcher = task_rules.RuleMatcher(actor)
    new_users = []
    for uid in to_add:  # validate everything before writing anything
        assignee = _load_assignee(uid)
        _authorize_assignee(actor, assignee, scope_type, scope_id, task.department_id, task.team_id,
                            matcher, action=RuleAction.ASSIGN)
        new_users.append(assignee)
    if to_remove:
        _require(actor, "assign", scope_type, scope_id)

    now = datetime.now(timezone.utc)
    for a in task.assignments:
        if a.unassigned_at is None and a.assignee_user_id in to_remove:
            a.unassigned_at = now
            a.end_reason = "REMOVED"
    for u in new_users:
        db.session.add(TaskAssignment(task_id=task.id, assignee_user_id=u.id, assigned_by_user_id=actor.id))
    db.session.flush()
    _notify_assigned(task, [u.id for u in new_users], actor)
    write_audit_log(
        user_id=actor.id, action="set_assignees", module=MODULE, entity_type=ENTITY_TYPE, entity_id=task.id,
        metadata={"added": to_add, "removed": to_remove}, ip_address=ip_address,
    )
    db.session.commit()
    db.session.refresh(task)
    return task


def refer_task(actor: User, task_id: int, payload: TaskRefer, *, ip_address: str | None) -> TaskAssignment:
    """An assignee refers the task onward. The chain is kept: the new assignment points
    at the referrer's, and the referrer's closes with end_reason=REFERRED. The recipient
    must belong to the task's team / department, and can refer it further in turn."""
    task = _get_or_404(task_id)
    _assert_in_units(Authority(actor), task)
    mine = (
        db.session.query(TaskAssignment)
        .filter(TaskAssignment.task_id == task.id, TaskAssignment.assignee_user_id == actor.id,
                TaskAssignment.unassigned_at.is_(None))
        .first()
    )
    if mine is None:
        raise PermissionDeniedError("permission_denied", "Only a current assignee can refer this task.")
    if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        raise ConflictError("A completed or cancelled task cannot be referred.")
    if payload.to_user_id == actor.id:
        raise ConflictError("You cannot refer a task to yourself.")
    recipient = _load_assignee(payload.to_user_id)
    if not recipient.is_active:
        raise ConflictError("This user is not active.")
    _check_assignee_belongs(recipient, task.department_id, task.team_id)
    if payload.to_user_id in task.assignee_ids:
        raise ConflictError("This user is already assigned to this task.")

    mine.unassigned_at = datetime.now(timezone.utc)
    mine.end_reason = "REFERRED"
    new = TaskAssignment(
        task_id=task.id, assignee_user_id=recipient.id, assigned_by_user_id=actor.id,
        parent_assignment_id=mine.id, referral_note=payload.note,
    )
    db.session.add(new)
    db.session.flush()
    _notify_assigned(task, [recipient.id], actor, "TASK_REFERRED", payload.note)
    write_audit_log(
        user_id=actor.id, action="refer", module=MODULE, entity_type=ENTITY_TYPE, entity_id=task.id,
        metadata={"from_user_id": actor.id, "to_user_id": recipient.id, "note": payload.note}, ip_address=ip_address,
    )
    db.session.commit()
    return new


def list_assignments(actor: User, task_id: int) -> list[dict]:
    """Full assignment history incl. the referral chain (who handed it to whom, and why)."""
    task = _viewable_task_or_403(actor, task_id)
    rows = (
        db.session.query(TaskAssignment).filter(TaskAssignment.task_id == task.id)
        .order_by(TaskAssignment.id).all()
    )
    names = _names_for({r.assignee_user_id for r in rows} | {r.assigned_by_user_id for r in rows})
    return [
        {
            "id": r.id,
            "assignee_user_id": r.assignee_user_id,
            "assignee_name": names.get(r.assignee_user_id, "Deleted user"),
            "assigned_by_user_id": r.assigned_by_user_id,
            "assigned_by_name": names.get(r.assigned_by_user_id, "Deleted user"),
            "parent_assignment_id": r.parent_assignment_id,
            "is_active": r.unassigned_at is None,
            "end_reason": r.end_reason,
            "referral_note": r.referral_note,
            "assigned_at": _iso_utc(r.assigned_at),
            "unassigned_at": _iso_utc(r.unassigned_at),
        }
        for r in rows
    ]


# ====================================================================
# Attachments (any number per task)
# ====================================================================
def _dump_file(f: TaskFile) -> dict:
    return {
        "id": f.id, "task_id": f.task_id, "name": f.original_name, "size": f.size,
        "content_type": f.content_type, "uploaded_by_user_id": f.uploaded_by_user_id,
        "uploaded_by_name": f.uploaded_by.full_name if f.uploaded_by else None,
        "created_at": _iso_utc(f.created_at),
    }


def list_files(actor: User, task_id: int) -> list[dict]:
    task = _viewable_task_or_403(actor, task_id)
    rows = db.session.query(TaskFile).filter(TaskFile.task_id == task.id).order_by(TaskFile.created_at, TaskFile.id).all()
    return [_dump_file(f) for f in rows]


def upload_files(actor: User, task_id: int, uploads: list, *, ip_address: str | None) -> list[dict]:
    """Attach one or many files in a single request (all-or-nothing)."""
    task = _viewable_task_or_403(actor, task_id)
    if not (_is_assignee(actor, task) or _can_manage_task(actor, task)):
        raise PermissionDeniedError("permission_denied", "Only the task's people can attach files.")
    if not uploads:
        from werkzeug.exceptions import BadRequest
        raise BadRequest("No file was sent. Use the form field named 'files'.")
    saved: list[TaskFile] = []
    try:
        for up in uploads:
            saved.append(task_files.save_task_file(task.id, up, uploaded_by_user_id=actor.id))
        db.session.flush()
        write_audit_log(
            user_id=actor.id, action="file_add", module=MODULE, entity_type=ENTITY_TYPE, entity_id=task.id,
            metadata={"files": [f.original_name for f in saved]}, ip_address=ip_address,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        for f in saved:
            task_files.remove_from_disk(f)
        raise
    return [_dump_file(f) for f in saved]


def get_file_for_download(actor: User, task_id: int, file_id: str) -> tuple[TaskFile, str]:
    task = _viewable_task_or_403(actor, task_id)
    row = db.session.get(TaskFile, file_id)
    if row is None or row.task_id != task.id:
        raise NotFoundError("File was not found.")
    return row, task_files.disk_path(row)


def delete_file(actor: User, task_id: int, file_id: str, *, ip_address: str | None) -> None:
    task = _viewable_task_or_403(actor, task_id)
    row = db.session.get(TaskFile, file_id)
    if row is None or row.task_id != task.id:
        raise NotFoundError("File was not found.")
    if row.uploaded_by_user_id != actor.id:
        _assert_manager(Authority(actor), task, "delete a file someone else attached")
    task_files.remove_from_disk(row)
    db.session.delete(row)
    write_audit_log(
        user_id=actor.id, action="file_delete", module=MODULE, entity_type=ENTITY_TYPE, entity_id=task.id,
        metadata={"file_id": file_id, "name": row.original_name}, ip_address=ip_address,
    )
    db.session.commit()


def can_manage_flags(actor: User, tasks: list[Task]) -> dict[int, bool]:
    """task id -> may the actor act as «مدیر» of it (one Authority for the whole page)."""
    auth = Authority(actor)
    return {t.id: auth.is_manager(t) for t in tasks}
