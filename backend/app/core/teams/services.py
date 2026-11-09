"""
Service layer for /api/core/teams -- Phase 4. See
app/core/departments/services.py's module docstring for why permission
checks live here rather than in routes.py.

Permission key: core.team.<action>. Scope rules:
    - create: (DEPARTMENT, payload.department_id).
    - read/update/delete: (TEAM, team.id).
    - list: permission-only check, then filtered by every DEPARTMENT-
      scoped grant (-> all teams under that department) or TEAM-scoped
      grant (-> that team only) the actor holds; GLOBAL sees everything.
      An ORGANIZATION-scoped grant also structurally covers every team
      under that org per scope_covers, so it is included too.

Team membership (`team_members`) is managed as a nested resource under
Teams (`POST`/`DELETE /api/core/teams/<id>/members`) rather than its own
top-level CRUD module -- IMPLEMENTATION_PLAN.md's Phase 4 goal lists six
resources, not team membership as a seventh; treating membership as part
of "managing a team" and gating it under the existing core.team.update
permission avoids inventing a new permission action beyond the
documented create/read/update/delete set.
"""
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import ScopeType
from app.core.departments.models import Department
from app.core.teams.models import Team, TeamMember
from app.core.teams.schemas import TeamCreate, TeamUpdate
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import get_matching_grants, has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "team"


def _require(actor: User, action: str, scope_type: ScopeType | None, scope_id: int | None) -> None:
    key = f"core.team.{action}"
    if not has_permission(actor, key, scope_type, scope_id):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(team_id: int) -> Team:
    team = db.session.get(Team, team_id)
    if team is None or team.deleted_at is not None:
        raise NotFoundError(f"Team {team_id} was not found.")
    return team


def _get_department_or_404(department_id: int) -> Department:
    dept = db.session.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise NotFoundError(f"Department {department_id} was not found.")
    return dept


def _get_user_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise NotFoundError(f"User {user_id} was not found.")
    return user


def list_teams(actor: User, *, page: int, per_page: int, include_inactive: bool = False):
    _require(actor, "read", None, None)

    query = db.session.query(Team).filter(Team.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Team.is_active.is_(True))

    grants = get_matching_grants(actor, "core.team.read")
    if not any(g.scope_type == ScopeType.GLOBAL for g in grants):
        team_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.TEAM}
        dept_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.DEPARTMENT}
        org_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}

        conditions = []
        if team_ids:
            conditions.append(Team.id.in_(team_ids))
        if dept_ids:
            conditions.append(Team.department_id.in_(dept_ids))
        if org_ids:
            org_dept_ids = {
                d.id for d in db.session.query(Department.id)
                .filter(Department.organization_id.in_(org_ids)).all()
            }
            if org_dept_ids:
                conditions.append(Team.department_id.in_(org_dept_ids))

        query = query.filter(db.or_(*conditions)) if conditions else query.filter(db.false())

    query = query.order_by(Team.id)
    return paginate_query(query, page, per_page)


def get_team(actor: User, team_id: int) -> Team:
    team = _get_or_404(team_id)
    _require(actor, "read", ScopeType.TEAM, team.id)
    return team


def create_team(actor: User, payload: TeamCreate, *, ip_address: str | None) -> Team:
    _get_department_or_404(payload.department_id)
    _require(actor, "create", ScopeType.DEPARTMENT, payload.department_id)

    if payload.manager_user_id is not None:
        _get_user_or_404(payload.manager_user_id)

    team = Team(
        name=payload.name,
        department_id=payload.department_id,
        manager_user_id=payload.manager_user_id,
    )
    db.session.add(team)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not create team (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=team.id, metadata={"name": team.name, "department_id": team.department_id},
        ip_address=ip_address,
    )
    db.session.commit()
    return team


def update_team(actor: User, team_id: int, payload: TeamUpdate, *, ip_address: str | None) -> Team:
    team = _get_or_404(team_id)
    _require(actor, "update", ScopeType.TEAM, team.id)

    changes = payload.model_dump(exclude_unset=True)
    if "manager_user_id" in changes and changes["manager_user_id"] is not None:
        _get_user_or_404(changes["manager_user_id"])

    for field, value in changes.items():
        setattr(team, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update team (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=team.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return team


def delete_team(actor: User, team_id: int, *, ip_address: str | None) -> None:
    team = _get_or_404(team_id)
    _require(actor, "delete", ScopeType.TEAM, team.id)

    team.deleted_at = datetime.now(timezone.utc)
    team.is_active = False

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=team.id, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Team membership -- nested under core.team.update.
# ---------------------------------------------------------------------


def list_team_members(actor: User, team_id: int) -> list[TeamMember]:
    """Read-only -- gated the same as reading the team itself (no GET
    existed before; the admin panel's team-detail dialog needs to show
    current membership)."""
    team = _get_or_404(team_id)
    _require(actor, "read", ScopeType.TEAM, team.id)
    return db.session.query(TeamMember).filter(TeamMember.team_id == team.id).all()


def add_team_member(actor: User, team_id: int, user_id: int, *, ip_address: str | None) -> TeamMember:
    team = _get_or_404(team_id)
    _require(actor, "update", ScopeType.TEAM, team.id)
    _get_user_or_404(user_id)

    existing = (
        db.session.query(TeamMember)
        .filter(TeamMember.team_id == team.id, TeamMember.user_id == user_id)
        .first()
    )
    if existing is not None:
        raise ConflictError("This user is already a member of this team.")

    member = TeamMember(team_id=team.id, user_id=user_id)
    db.session.add(member)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not add team member (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="add_member", module=MODULE, entity_type="team_member",
        entity_id=member.id, metadata={"team_id": team.id, "user_id": user_id}, ip_address=ip_address,
    )
    db.session.commit()
    return member


def remove_team_member(actor: User, team_id: int, user_id: int, *, ip_address: str | None) -> None:
    team = _get_or_404(team_id)
    _require(actor, "update", ScopeType.TEAM, team.id)

    member = (
        db.session.query(TeamMember)
        .filter(TeamMember.team_id == team.id, TeamMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise NotFoundError("This user is not a member of this team.")

    db.session.delete(member)
    write_audit_log(
        user_id=actor.id, action="remove_member", module=MODULE, entity_type="team_member",
        entity_id=member.id, metadata={"team_id": team.id, "user_id": user_id}, ip_address=ip_address,
    )
    db.session.commit()
