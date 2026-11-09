"""
"Who may define / assign tasks to whom" -- stored in task_assignment_rules.

Managing the rules is limited to admins and holders of
`core.permission.update`. Enforcement lives in services.py through
`RuleMatcher` / `assert_can_assign_to`.

Semantics
    * Admins may create-for / assign-to anyone.
    * Everybody may create a task for / assign a task to themselves.
    * Anyone else may only act on users matched by an active rule whose
      grantor is the actor (USER rule) or one of the actor's active roles
      (ROLE rule), whose target matches the user (ALL | USER | ROLE |
      DEPARTMENT | TEAM), and whose `action` covers what is being done:
      CREATE ("X may create a task already assigned to Y"), ASSIGN ("X
      may assign an existing task to Y"), or BOTH. This is what lets an
      admin express "X -> Y -> Create/Assign Task".
"""
from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import UserRole
from app.core.departments.models import Department
from app.core.roles.models import Role
from app.core.teams.models import Team, TeamMember
from app.core.users.models import User
from app.extensions import db
from app.modules.tasks.models import RuleAction, RuleSubject, RuleTarget, TaskAssignmentRule
from app.modules.tasks.schemas import AssignmentRuleCreate
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission, is_admin
from app.utils.exceptions import ConflictError, NotFoundError

MODULE = "tasks"
ENTITY_TYPE = "task_assignment_rule"


def can_manage_rules(actor: User) -> bool:
    return is_admin(actor) or has_permission(actor, "core.permission.update")


# ---- unit isolation for rule management ---------------------------------
# Only an admin manages rules across every unit. A non-admin holder of
# `core.permission.update` may only see / create / delete rules whose grantor AND
# target lie entirely inside their own unit (own department + the departments of the
# teams they belong to). Rules that name a ROLE or "everyone" cross unit lines by
# definition, so they stay admin-only.
def _actor_department_ids(actor: User) -> set[int]:
    ids = {actor.department_id} if actor.department_id else set()
    rows = (
        db.session.query(Team.department_id)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .filter(TeamMember.user_id == actor.id, Team.deleted_at.is_(None))
    )
    return ids | {r[0] for r in rows}


def _user_in_units(user_id: int | None, dept_ids: set[int]) -> bool:
    user = db.session.get(User, user_id) if user_id else None
    return user is not None and user.department_id in dept_ids


def _within_units(grantor_type, grantor_id, target_type, target_id, dept_ids: set[int]) -> bool:
    if grantor_type != RuleSubject.USER or not _user_in_units(grantor_id, dept_ids):
        return False
    if target_type == RuleTarget.USER:
        return _user_in_units(target_id, dept_ids)
    if target_type == RuleTarget.DEPARTMENT:
        return target_id in dept_ids
    if target_type == RuleTarget.TEAM:
        team = db.session.get(Team, target_id) if target_id else None
        return team is not None and team.department_id in dept_ids
    return False  # ALL / ROLE -> admin only


def can_view_rules(actor: User) -> bool:
    return can_manage_rules(actor) or has_permission(actor, "core.permission.read")


def _active_role_ids(user_id: int) -> set[int]:
    rows = (
        db.session.query(UserRole.role_id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user_id, Role.is_active.is_(True), Role.deleted_at.is_(None))
        .all()
    )
    return {r[0] for r in rows}


class RuleMatcher:
    """Loads the actor's rules once, then answers `allows(assignee, action)`.

    `action` is RuleAction.CREATE or RuleAction.ASSIGN -- the concrete
    thing being attempted. A stored rule with action=BOTH covers either.
    """

    def __init__(self, actor: User):
        self.actor = actor
        self.admin = is_admin(actor)
        self.rules: list[TaskAssignmentRule] = []
        self._roles: dict[int, set[int]] = {}
        self._teams: dict[int, set[int]] = {}
        if self.admin:
            return
        role_ids = _active_role_ids(actor.id)
        q = db.session.query(TaskAssignmentRule).filter(TaskAssignmentRule.is_active.is_(True))
        conds = [db.and_(TaskAssignmentRule.grantor_type == RuleSubject.USER,
                         TaskAssignmentRule.grantor_id == actor.id)]
        if role_ids:
            conds.append(db.and_(TaskAssignmentRule.grantor_type == RuleSubject.ROLE,
                                 TaskAssignmentRule.grantor_id.in_(role_ids)))
        self.rules = q.filter(db.or_(*conds)).all()
        if any(r.target_type == RuleTarget.ROLE for r in self.rules):
            for uid, rid in db.session.query(UserRole.user_id, UserRole.role_id).all():
                self._roles.setdefault(uid, set()).add(rid)
        if any(r.target_type == RuleTarget.TEAM for r in self.rules):
            for uid, tid in db.session.query(TeamMember.user_id, TeamMember.team_id).all():
                self._teams.setdefault(uid, set()).add(tid)

    def allows(self, assignee: User, action: RuleAction = RuleAction.ASSIGN) -> bool:
        if self.admin or assignee.id == self.actor.id:
            return True
        for r in self.rules:
            if r.action != RuleAction.BOTH and r.action != action:
                continue
            t = r.target_type
            if t == RuleTarget.ALL:
                return True
            if t == RuleTarget.USER and r.target_id == assignee.id:
                return True
            if t == RuleTarget.DEPARTMENT and r.target_id == assignee.department_id:
                return True
            if t == RuleTarget.ROLE and r.target_id in self._roles.get(assignee.id, set()):
                return True
            if t == RuleTarget.TEAM and r.target_id in self._teams.get(assignee.id, set()):
                return True
        return False


def assert_can_assign_to(actor: User, assignee: User, matcher: RuleMatcher | None = None,
                         action: RuleAction = RuleAction.ASSIGN) -> None:
    matcher = matcher or RuleMatcher(actor)
    if not matcher.allows(assignee, action):
        verb = "create tasks for" if action == RuleAction.CREATE else "assign tasks to"
        raise PermissionDeniedError(
            "permission_denied",
            f"You are not allowed to {verb} '{assignee.full_name}'. "
            "Ask an administrator to add a task assignment rule.",
        )


def assignable_users(actor: User, action: RuleAction = RuleAction.ASSIGN) -> list[User]:
    matcher = RuleMatcher(actor)
    users = (
        db.session.query(User)
        .filter(User.deleted_at.is_(None), User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    return [u for u in users if matcher.allows(u, action)]


# ---------------------------------------------------------------- CRUD
def _label(kind: str, ident: int | None) -> str:
    if kind == "ALL":
        return "Everyone"
    if ident is None:
        return "—"
    model = {"USER": User, "ROLE": Role, "DEPARTMENT": Department, "TEAM": Team}[kind]
    row = db.session.get(model, ident)
    if row is None:
        return f"#{ident} (missing)"
    return getattr(row, "full_name", None) or getattr(row, "display_name", None) or row.name


def dump_rule(r: TaskAssignmentRule) -> dict:
    gt, tt = r.grantor_type.value, r.target_type.value
    return {
        "id": r.id,
        "grantor_type": gt, "grantor_id": r.grantor_id, "grantor_label": _label(gt, r.grantor_id),
        "target_type": tt, "target_id": r.target_id, "target_label": _label(tt, r.target_id),
        "action": r.action.value,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def list_rules(actor: User) -> list[dict]:
    if not can_view_rules(actor):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'core.permission.read' for this action."
        )
    rows = (
        db.session.query(TaskAssignmentRule)
        .filter(TaskAssignmentRule.is_active.is_(True))
        .order_by(TaskAssignmentRule.id)
        .all()
    )
    if not is_admin(actor):
        dept_ids = _actor_department_ids(actor)
        rows = [r for r in rows if _within_units(r.grantor_type, r.grantor_id, r.target_type, r.target_id, dept_ids)]
    return [dump_rule(r) for r in rows]


def _exists(model, ident: int) -> bool:
    row = db.session.get(model, ident)
    return row is not None and getattr(row, "deleted_at", None) is None


def create_rule(actor: User, payload: AssignmentRuleCreate, *, ip_address: str | None) -> dict:
    if not can_manage_rules(actor):
        raise PermissionDeniedError(
            "permission_denied", "Only administrators or holders of 'core.permission.update' can manage task rules."
        )
    if not is_admin(actor) and not _within_units(
        payload.grantor_type, payload.grantor_id,
        payload.target_type, None if payload.target_type == RuleTarget.ALL else payload.target_id,
        _actor_department_ids(actor),
    ):
        raise PermissionDeniedError(
            "permission_denied", "You can only manage task rules inside your own department."
        )
    grantor_model = User if payload.grantor_type == RuleSubject.USER else Role
    if not _exists(grantor_model, payload.grantor_id):
        raise NotFoundError(f"{payload.grantor_type.value.title()} {payload.grantor_id} was not found.")

    target_id = payload.target_id
    if payload.target_type == RuleTarget.ALL:
        target_id = None
    else:
        if target_id is None:
            raise ConflictError("target_id is required for this target type.")
        target_model = {
            RuleTarget.USER: User, RuleTarget.ROLE: Role,
            RuleTarget.DEPARTMENT: Department, RuleTarget.TEAM: Team,
        }[payload.target_type]
        if not _exists(target_model, target_id):
            raise NotFoundError(f"{payload.target_type.value.title()} {target_id} was not found.")

    # Two rules for the same grantor+target are fine as long as their
    # actions don't overlap (e.g. a CREATE-only rule and a separate
    # ASSIGN-only rule) -- BOTH overlaps with everything.
    dup = (
        db.session.query(TaskAssignmentRule)
        .filter(
            TaskAssignmentRule.is_active.is_(True),
            TaskAssignmentRule.grantor_type == payload.grantor_type,
            TaskAssignmentRule.grantor_id == payload.grantor_id,
            TaskAssignmentRule.target_type == payload.target_type,
            TaskAssignmentRule.target_id.is_(None) if target_id is None
            else TaskAssignmentRule.target_id == target_id,
            db.or_(
                TaskAssignmentRule.action == RuleAction.BOTH,
                TaskAssignmentRule.action == payload.action,
            ) if payload.action != RuleAction.BOTH else True,
        )
        .first()
    )
    if dup is not None:
        raise ConflictError("This rule already exists.")

    rule = TaskAssignmentRule(
        grantor_type=payload.grantor_type, grantor_id=payload.grantor_id,
        target_type=payload.target_type, target_id=target_id, action=payload.action,
        is_active=True, created_by_user_id=actor.id,
    )
    db.session.add(rule)
    db.session.flush()
    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE, entity_id=rule.id,
        metadata={"grantor": f"{payload.grantor_type.value}:{payload.grantor_id}",
                  "target": f"{payload.target_type.value}:{target_id}"},
        ip_address=ip_address,
    )
    db.session.commit()
    return dump_rule(rule)


def delete_rule(actor: User, rule_id: int, *, ip_address: str | None) -> None:
    if not can_manage_rules(actor):
        raise PermissionDeniedError(
            "permission_denied", "Only administrators or holders of 'core.permission.update' can manage task rules."
        )
    rule = db.session.get(TaskAssignmentRule, rule_id)
    if rule is None or not rule.is_active:
        raise NotFoundError(f"Rule {rule_id} was not found.")
    if not is_admin(actor) and not _within_units(
        rule.grantor_type, rule.grantor_id, rule.target_type, rule.target_id, _actor_department_ids(actor)
    ):
        raise PermissionDeniedError(
            "permission_denied", "You can only manage task rules inside your own department."
        )
    rule.is_active = False
    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE, entity_id=rule.id,
        ip_address=ip_address,
    )
    db.session.commit()
