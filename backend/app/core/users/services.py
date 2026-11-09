"""
Service layer for /api/core/users -- Phase 4. See
app/core/departments/services.py's module docstring for why permission
checks live here rather than in routes.py.

Permission key: core.user.<action>. Scope rules:
    - create: department_id given -> (DEPARTMENT, department_id); else
      organization_id given -> (ORGANIZATION, organization_id); else
      (GLOBAL, None) -- creating a user with no organizational placement
      is a GLOBAL-only action.
    - read/update/delete (single row): resolved the same way, but from
      the EXISTING row's own organization_id/department_id (never from
      the acting user's own placement -- AUTHORIZATION.md §5 step 2).
    - list: permission-only check, then filtered by every grant the
      actor holds for core.user.read: DEPARTMENT-scoped ->
      users.department_id match; ORGANIZATION-scoped ->
      users.organization_id match; TEAM-scoped -> users who are members
      of that team (via team_members); GLOBAL -> everyone.

Role assignment (`user_roles`) is nested under Users
(`POST`/`DELETE /api/core/users/<id>/roles`) and gated under
core.user.update, for the same reason team membership is nested under
Teams in app/core/teams/services.py -- it is part of "managing a user's
placement/access," not a new permission action beyond the documented
create/read/update/delete set.
"""
from datetime import datetime, timezone

from app.core.audit_logs.services import write_audit_log
from app.core.auth import services as auth_services
from app.core.authorization.models import ScopeType, UserRole
from app.core.departments.models import Department
from app.core.organizations.models import Organization
from app.core.roles.models import Role
from app.core.teams.models import TeamMember
from app.core.users.models import User
from app.core.users.schemas import UserCreate, UserUpdate
from app.extensions import db
from app.permissions import matrix as permission_matrix
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import get_matching_grants, has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "user"


def _require(actor: User, action: str, scope_type: ScopeType | None, scope_id: int | None) -> None:
    key = f"core.user.{action}"
    if not has_permission(actor, key, scope_type, scope_id):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _scope_for_placement(
    organization_id: int | None, department_id: int | None
) -> tuple[ScopeType, int | None]:
    if department_id is not None:
        return ScopeType.DEPARTMENT, department_id
    if organization_id is not None:
        return ScopeType.ORGANIZATION, organization_id
    return ScopeType.GLOBAL, None


def _get_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise NotFoundError(f"User {user_id} was not found.")
    return user


def list_users(
    actor: User, *, page: int, per_page: int, include_inactive: bool = False, search: str | None = None
):
    _require(actor, "read", None, None)

    query = db.session.query(User).filter(User.deleted_at.is_(None))
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.filter(
            db.or_(
                db.func.lower(User.full_name).like(like),
                db.func.lower(User.email).like(like),
                db.func.lower(User.username).like(like),
            )
        )

    grants = get_matching_grants(actor, "core.user.read")
    if not any(g.scope_type == ScopeType.GLOBAL for g in grants):
        dept_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.DEPARTMENT}
        org_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.ORGANIZATION}
        team_ids = {g.scope_id for g in grants if g.scope_type == ScopeType.TEAM}

        conditions = []
        if dept_ids:
            conditions.append(User.department_id.in_(dept_ids))
        if org_ids:
            conditions.append(User.organization_id.in_(org_ids))
        if team_ids:
            team_user_ids = {
                row.user_id for row in db.session.query(TeamMember.user_id)
                .filter(TeamMember.team_id.in_(team_ids)).all()
            }
            if team_user_ids:
                conditions.append(User.id.in_(team_user_ids))

        query = query.filter(db.or_(*conditions)) if conditions else query.filter(db.false())

    query = query.order_by(User.id)
    return paginate_query(query, page, per_page)


def get_user(actor: User, user_id: int) -> User:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "read", scope_type, scope_id)
    return user


def create_user(actor: User, payload: UserCreate, *, ip_address: str | None) -> User:
    if payload.organization_id is not None and db.session.get(Organization, payload.organization_id) is None:
        raise NotFoundError(f"Organization {payload.organization_id} was not found.")
    if payload.department_id is not None and db.session.get(Department, payload.department_id) is None:
        raise NotFoundError(f"Department {payload.department_id} was not found.")

    scope_type, scope_id = _scope_for_placement(payload.organization_id, payload.department_id)
    _require(actor, "create", scope_type, scope_id)

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        username=payload.username,
        password_hash=auth_services.hash_password(payload.password),
        organization_id=payload.organization_id,
        department_id=payload.department_id,
    )
    db.session.add(user)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("A user with this email or username already exists.") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=user.id, metadata={"username": user.username, "email": user.email},
        ip_address=ip_address,
    )
    db.session.commit()
    return user


def set_user_password(actor: User, user_id: int, new_password: str, *, ip_address: str | None) -> None:
    """An admin sets a new password for a user (forgotten password / first login).

    Admin-only on purpose: resetting a password is the same as taking over the account, so
    a delegated `core.user.update` must not be enough (it would let a department-level
    editor take over an admin). The user's sessions are signed out; the old password
    cannot be recovered or shown -- it only exists as an Argon2 hash.
    """
    from app.permissions.service import is_admin

    user = _get_or_404(user_id)
    if not is_admin(actor):
        raise PermissionDeniedError("permission_denied", "Only an administrator can set another user's password.")
    user.password_hash = auth_services.hash_password(new_password)
    auth_services._revoke_all_active_tokens_for_user(user.id, now=datetime.now(timezone.utc))
    write_audit_log(
        user_id=actor.id, action="password_reset", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=user.id, metadata=None, ip_address=ip_address,
    )
    db.session.commit()


def update_user(actor: User, user_id: int, payload: UserUpdate, *, ip_address: str | None) -> User:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "update", scope_type, scope_id)

    changes = payload.model_dump(exclude_unset=True)
    # Non-nullable columns: an explicit null means "no change", never "set NULL".
    for non_nullable in ("full_name", "email", "username", "is_active"):
        if non_nullable in changes and changes[non_nullable] is None:
            del changes[non_nullable]
    if "organization_id" in changes and changes["organization_id"] is not None:
        if db.session.get(Organization, changes["organization_id"]) is None:
            raise NotFoundError(f"Organization {changes['organization_id']} was not found.")
    if "department_id" in changes and changes["department_id"] is not None:
        if db.session.get(Department, changes["department_id"]) is None:
            raise NotFoundError(f"Department {changes['department_id']} was not found.")

    if changes.get("is_active") is False and user.id == actor.id:
        raise ConflictError("A user cannot deactivate their own account.")

    for field, value in changes.items():
        setattr(user, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update user (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=user.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return user


def delete_user(actor: User, user_id: int, *, ip_address: str | None) -> None:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "delete", scope_type, scope_id)

    if user.id == actor.id:
        raise ConflictError("A user cannot delete their own account.")

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=user.id, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Role assignment -- nested under core.user.update.
# ---------------------------------------------------------------------


def list_user_roles(actor: User, user_id: int) -> list[UserRole]:
    """Read-only -- gated the same as reading the user itself (Phase 5:
    the admin panel's user-detail page needs to show currently-assigned
    roles, which no existing endpoint exposed)."""
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "read", scope_type, scope_id)
    return db.session.query(UserRole).filter(UserRole.user_id == user.id).all()


def assign_role(
    actor: User, user_id: int, role_id: int, organization_id: int | None, *, ip_address: str | None
) -> UserRole:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "update", scope_type, scope_id)

    role = db.session.get(Role, role_id)
    if role is None or role.deleted_at is not None:
        raise NotFoundError(f"Role {role_id} was not found.")
    if organization_id is not None and db.session.get(Organization, organization_id) is None:
        raise NotFoundError(f"Organization {organization_id} was not found.")

    existing = (
        db.session.query(UserRole)
        .filter(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
            UserRole.organization_id == organization_id,
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("This user already holds this role in this context.")

    user_role = UserRole(user_id=user.id, role_id=role.id, organization_id=organization_id)
    db.session.add(user_role)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not assign role (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="assign_role", module=MODULE, entity_type="user_role",
        entity_id=user_role.id, metadata={"user_id": user.id, "role_id": role.id}, ip_address=ip_address,
    )
    db.session.commit()
    return user_role


def revoke_role(actor: User, user_id: int, role_id: int, *, ip_address: str | None) -> None:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "update", scope_type, scope_id)

    user_role = (
        db.session.query(UserRole)
        .filter(UserRole.user_id == user.id, UserRole.role_id == role_id)
        .first()
    )
    if user_role is None:
        raise NotFoundError("This user does not hold this role.")

    db.session.delete(user_role)
    write_audit_log(
        user_id=actor.id, action="revoke_role", module=MODULE, entity_type="user_role",
        entity_id=user_role.id, metadata={"user_id": user.id, "role_id": role_id}, ip_address=ip_address,
    )
    db.session.commit()


# ---------------------------------------------------------------------
# Per-user permission management (matrix + effective access).
#
# Reading  : core.user.read at the user's scope (same as viewing the user).
# Writing  : core.user.update at the user's scope AND core.permission.update
#            (GLOBAL) -- managing who can do what is permission-management,
#            which AUTHORIZATION.md §9 treats as its own privileged
#            category, so user-update alone is not enough.
# Guards   : nobody may edit their OWN permissions, and an actor may only
#            ALLOW a permission they hold themselves (no escalation).
# ---------------------------------------------------------------------


def get_access_summary(actor: User, user_id: int) -> dict:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "read", scope_type, scope_id)
    return permission_matrix.get_user_access_summary(user)


def get_permission_matrix(actor: User, user_id: int) -> dict:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "read", scope_type, scope_id)
    return permission_matrix.get_user_matrix(user)


def set_permission_matrix(
    actor: User, user_id: int, cells: dict, *, ip_address: str | None
) -> dict:
    user = _get_or_404(user_id)
    scope_type, scope_id = _scope_for_placement(user.organization_id, user.department_id)
    _require(actor, "update", scope_type, scope_id)
    if not has_permission(actor, "core.permission.update", ScopeType.GLOBAL, None):
        raise PermissionDeniedError(
            "permission_denied", "Missing permission 'core.permission.update' for this action."
        )
    if user.id == actor.id:
        raise PermissionDeniedError(
            "permission_denied", "You cannot change your own permissions."
        )

    try:
        to_allow = permission_matrix.desired_true_keys(cells)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc
    for key in to_allow:
        if not has_permission(actor, key):
            raise PermissionDeniedError(
                "permission_denied",
                f"You cannot grant '{key}' because you do not hold it yourself.",
            )

    changes = permission_matrix.apply_user_matrix(user, cells, actor)
    write_audit_log(
        user_id=actor.id, action="set_permissions", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=user.id, metadata={"changes": changes}, ip_address=ip_address,
    )
    db.session.commit()
    return permission_matrix.get_user_matrix(user)
