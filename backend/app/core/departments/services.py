"""
Service layer for /api/core/departments -- Phase 4.

Permission checks live in the service layer (not routes.py) for every
Phase 4 resource, uniformly, because two of the five actions need scope
information that a route-level decorator (bound to URL path params
alone) can't see:
    - CREATE's target scope comes from the parsed request body (which
      organization the new row will belong to), not a URL param.
    - LIST needs to filter rows by the union of the actor's covering
      grants, not just allow/deny a single scope.
Doing all five actions the same way (manual `has_permission`/
`get_matching_grants` calls here) keeps one consistent pattern across
every Phase 4 module instead of splitting CREATE/LIST from READ/UPDATE/
DELETE across two different mechanisms.

Permission key: core.department.<action>. Scope rules:
    - create: (ORGANIZATION, payload.organization_id) -- the actor must
      hold an ORGANIZATION-or-broader grant covering the org the new
      department will belong to.
    - read/update/delete: (DEPARTMENT, department.id).
    - list: permission-only check, then filtered by every ORGANIZATION-
      or DEPARTMENT-scoped grant the actor holds (GLOBAL sees
      everything; TEAM-scoped grants can't structurally cover a
      DEPARTMENT target per scope_covers, so they contribute nothing).
"""
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import ScopeType
from app.core.departments.models import Department
from app.core.departments.schemas import DepartmentCreate, DepartmentUpdate
from app.core.organizations.models import Organization
from app.core.teams.models import Team
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import get_matching_grants, has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "department"


def _require(actor: User, action: str, scope_type: ScopeType | None, scope_id: int | None) -> None:
    key = f"core.department.{action}"
    if not has_permission(actor, key, scope_type, scope_id):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(department_id: int) -> Department:
    dept = db.session.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise NotFoundError(f"Department {department_id} was not found.")
    return dept


def _get_organization_or_404(organization_id: int) -> Organization:
    org = db.session.get(Organization, organization_id)
    if org is None or org.deleted_at is not None:
        raise NotFoundError(f"Organization {organization_id} was not found.")
    return org


def list_departments(actor: User, *, page: int, per_page: int, include_inactive: bool = False):
    _require(actor, "read", None, None)

    query = db.session.query(Department).filter(Department.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Department.is_active.is_(True))

    grants = get_matching_grants(actor, "core.department.read")
    if not any(g.scope_type == ScopeType.GLOBAL for g in grants):
        org_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}
        dept_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.DEPARTMENT}
        if org_ids or dept_ids:
            conditions = []
            if org_ids:
                conditions.append(Department.organization_id.in_(org_ids))
            if dept_ids:
                conditions.append(Department.id.in_(dept_ids))
            query = query.filter(db.or_(*conditions))
        else:
            query = query.filter(db.false())

    query = query.order_by(Department.id)
    return paginate_query(query, page, per_page)


def get_department(actor: User, department_id: int) -> Department:
    dept = _get_or_404(department_id)
    _require(actor, "read", ScopeType.DEPARTMENT, dept.id)
    return dept


def create_department(actor: User, payload: DepartmentCreate, *, ip_address: str | None) -> Department:
    _get_organization_or_404(payload.organization_id)
    _require(actor, "create", ScopeType.ORGANIZATION, payload.organization_id)

    if payload.parent_department_id is not None:
        _get_or_404(payload.parent_department_id)
    if payload.manager_user_id is not None and db.session.get(User, payload.manager_user_id) is None:
        raise NotFoundError(f"User {payload.manager_user_id} was not found.")

    dept = Department(
        name=payload.name,
        organization_id=payload.organization_id,
        parent_department_id=payload.parent_department_id,
        manager_user_id=payload.manager_user_id,
    )
    db.session.add(dept)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not create department (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=dept.id, metadata={"name": dept.name, "organization_id": dept.organization_id},
        ip_address=ip_address,
    )
    db.session.commit()
    return dept


def update_department(
    actor: User, department_id: int, payload: DepartmentUpdate, *, ip_address: str | None
) -> Department:
    dept = _get_or_404(department_id)
    _require(actor, "update", ScopeType.DEPARTMENT, dept.id)

    changes = payload.model_dump(exclude_unset=True)
    if "parent_department_id" in changes and changes["parent_department_id"] is not None:
        if changes["parent_department_id"] == dept.id:
            raise ConflictError("A department cannot be its own parent.")
        _get_or_404(changes["parent_department_id"])
    if "manager_user_id" in changes and changes["manager_user_id"] is not None:
        if db.session.get(User, changes["manager_user_id"]) is None:
            raise NotFoundError(f"User {changes['manager_user_id']} was not found.")

    for field, value in changes.items():
        setattr(dept, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update department (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=dept.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return dept


def delete_department(actor: User, department_id: int, *, ip_address: str | None) -> None:
    dept = _get_or_404(department_id)
    _require(actor, "delete", ScopeType.DEPARTMENT, dept.id)

    has_active_teams = (
        db.session.query(Team)
        .filter(Team.department_id == dept.id, Team.deleted_at.is_(None))
        .first()
    )
    if has_active_teams is not None:
        raise ConflictError("Cannot delete a department that still has active teams.")

    dept.deleted_at = datetime.now(timezone.utc)
    dept.is_active = False

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=dept.id, ip_address=ip_address,
    )
    db.session.commit()
