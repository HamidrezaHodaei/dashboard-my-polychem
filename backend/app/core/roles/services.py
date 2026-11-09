"""
Service layer for /api/core/roles -- Phase 4.

Roles carry no organizational scope of their own (the `roles` table has
no organization_id/department_id -- AUTHORIZATION.md's revision notes
keep roles strictly separate from departments), so every action here is
checked at GLOBAL scope only: managing the role catalog itself is a
platform-wide, not department/team-scoped, action. This also means list
never needs row-level filtering the way Users/Departments/Teams/
Organizations do -- the actor either holds a GLOBAL core.role.read grant
(sees every role) or doesn't (sees none, via the permission check
itself).
"""
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import RolePermissionScope, ScopeType, UserRole
from app.core.departments.models import Department
from app.core.organizations.models import Organization
from app.core.permissions.models import Permission
from app.core.roles.models import Role
from app.core.roles.schemas import RoleCreate, RolePermissionGrantCreate, RoleUpdate
from app.core.teams.models import Team
from app.core.users.models import User
from app.extensions import db
from app.permissions import matrix as permission_matrix
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "role"


def _require(actor: User, action: str) -> None:
    key = f"core.role.{action}"
    if not has_permission(actor, key, ScopeType.GLOBAL, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(role_id: int) -> Role:
    role = db.session.get(Role, role_id)
    if role is None or role.deleted_at is not None:
        raise NotFoundError(f"Role {role_id} was not found.")
    return role


def list_roles(actor: User, *, page: int, per_page: int, include_inactive: bool = False):
    _require(actor, "read")
    query = db.session.query(Role).filter(Role.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(Role.is_active.is_(True))
    query = query.order_by(Role.id)
    return paginate_query(query, page, per_page)


def get_role(actor: User, role_id: int) -> Role:
    _require(actor, "read")
    return _get_or_404(role_id)


def create_role(actor: User, payload: RoleCreate, *, ip_address: str | None) -> Role:
    _require(actor, "create")

    role = Role(
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        is_system_role=False,
    )
    db.session.add(role)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("A role with this name already exists.") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role.id, metadata={"name": role.name}, ip_address=ip_address,
    )
    db.session.commit()
    return role


def update_role(actor: User, role_id: int, payload: RoleUpdate, *, ip_address: str | None) -> Role:
    _require(actor, "update")
    role = _get_or_404(role_id)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(role, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update role (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return role


def delete_role(actor: User, role_id: int, *, ip_address: str | None) -> None:
    _require(actor, "delete")
    role = _get_or_404(role_id)

    if role.is_system_role:
        raise ConflictError("System roles cannot be deleted through ordinary admin CRUD.")

    still_held = db.session.query(UserRole).filter(UserRole.role_id == role.id).first()
    if still_held is not None:
        raise ConflictError("Cannot delete a role that is still held by at least one user.")

    role.deleted_at = datetime.now(timezone.utc)
    role.is_active = False

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role.id, ip_address=ip_address,
    )
    db.session.commit()


# --- Role -> permission grants -----------------------------------------
# No HTTP surface existed for this before (only scripts/seed_roles_
# permissions.py wrote role_permission_scopes rows directly), so a role
# created through the API had no way to actually be granted anything.
# Gated by core.role.update -- managing a role's permission set is a
# form of updating the role, same rationale as user-role assignment
# reusing core.user.update (app/core/users/services.py).

def _validate_scope(scope_type: ScopeType, scope_id: int | None) -> None:
    if scope_type in (ScopeType.GLOBAL, ScopeType.SELF):
        if scope_id is not None:
            raise ConflictError(f"scope_id must be null for {scope_type.value} scope.")
        return
    if scope_id is None:
        raise ConflictError(f"scope_id is required for {scope_type.value} scope.")

    model = {
        ScopeType.ORGANIZATION: Organization,
        ScopeType.DEPARTMENT: Department,
        ScopeType.TEAM: Team,
    }[scope_type]
    row = db.session.get(model, scope_id)
    if row is None or getattr(row, "deleted_at", None) is not None:
        raise NotFoundError(f"{scope_type.value.title()} {scope_id} was not found.")


def list_role_permissions(actor: User, role_id: int) -> list[RolePermissionScope]:
    _require(actor, "read")
    _get_or_404(role_id)
    return (
        db.session.query(RolePermissionScope)
        .filter(RolePermissionScope.role_id == role_id, RolePermissionScope.is_active.is_(True))
        .order_by(RolePermissionScope.id)
        .all()
    )


def grant_permission_to_role(
    actor: User, role_id: int, payload: RolePermissionGrantCreate, *, ip_address: str | None
) -> RolePermissionScope:
    _require(actor, "update")
    role = _get_or_404(role_id)

    permission = db.session.get(Permission, payload.permission_id)
    if permission is None:
        raise NotFoundError(f"Permission {payload.permission_id} was not found.")

    try:
        scope_type = ScopeType(payload.scope_type)
    except ValueError as exc:
        raise NotFoundError(f"'{payload.scope_type}' is not a recognized scope type.") from exc
    _validate_scope(scope_type, payload.scope_id)

    existing = (
        db.session.query(RolePermissionScope)
        .filter(
            RolePermissionScope.role_id == role.id,
            RolePermissionScope.permission_id == permission.id,
            RolePermissionScope.scope_type == scope_type,
            RolePermissionScope.scope_id == payload.scope_id,
        )
        .first()
    )
    if existing is not None:
        if existing.is_active:
            raise ConflictError("This role already holds this exact grant.")
        existing.is_active = True
        existing.granted_by_user_id = actor.id
        db.session.commit()
        return existing

    grant = RolePermissionScope(
        role_id=role.id,
        permission_id=permission.id,
        scope_type=scope_type,
        scope_id=payload.scope_id,
        is_active=True,
        granted_by_user_id=actor.id,
    )
    db.session.add(grant)
    db.session.flush()

    write_audit_log(
        user_id=actor.id, action="grant_permission", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role.id,
        metadata={"permission_id": permission.id, "scope_type": scope_type.value, "scope_id": payload.scope_id},
        ip_address=ip_address,
    )
    db.session.commit()
    return grant


def revoke_permission_from_role(
    actor: User, role_id: int, grant_id: int, *, ip_address: str | None
) -> None:
    _require(actor, "update")
    _get_or_404(role_id)

    grant = (
        db.session.query(RolePermissionScope)
        .filter(RolePermissionScope.id == grant_id, RolePermissionScope.role_id == role_id)
        .one_or_none()
    )
    if grant is None or not grant.is_active:
        raise NotFoundError(f"Grant {grant_id} was not found.")

    grant.is_active = False

    write_audit_log(
        user_id=actor.id, action="revoke_permission", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role_id, metadata={"grant_id": grant_id}, ip_address=ip_address,
    )
    db.session.commit()


# --- Role permission matrix (Module x Read/Create/Edit/Delete) -----------
# Gated like the grant endpoints above: read -> core.role.read,
# write -> core.role.update (GLOBAL).

def get_permission_matrix(actor: User, role_id: int) -> dict:
    _require(actor, "read")
    role = _get_or_404(role_id)
    return permission_matrix.get_role_matrix(role)


def set_permission_matrix(actor: User, role_id: int, cells: dict, *, ip_address: str | None) -> dict:
    _require(actor, "update")
    role = _get_or_404(role_id)
    try:
        permission_matrix.validate_cells(cells)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    # Lock-out guard: the seeded `admin` role must always keep every permission
    # the matrix manages -- otherwise one wrong click could leave nobody able
    # to manage access again.
    if role.name == "admin" and any(
        desired is False for actions in cells.values() for desired in actions.values()
    ):
        raise ConflictError("The admin role's permissions cannot be reduced.")

    # No escalation: only permissions the actor holds themselves may be granted to a role.
    for key in permission_matrix.desired_true_keys(cells):
        if not has_permission(actor, key):
            raise PermissionDeniedError(
                "permission_denied", f"You cannot grant '{key}' because you do not hold it yourself."
            )

    changes = permission_matrix.apply_role_matrix(role, cells, actor)
    write_audit_log(
        user_id=actor.id, action="set_permissions", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=role.id, metadata={"changes": changes}, ip_address=ip_address,
    )
    db.session.commit()
    return permission_matrix.get_role_matrix(role)
