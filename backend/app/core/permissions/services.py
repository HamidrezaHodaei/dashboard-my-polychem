"""
Service layer for /api/core/permissions -- Phase 4.

Same GLOBAL-only rationale as app/core/roles/services.py: the
`permissions` table has no organizational scope of its own.

Permission has no `deleted_at` (Permission model docstring: "the
canonical set is managed via the Phase 2 registry/migrations, not via ad
hoc soft deletion") -- so delete here is a genuine hard DELETE, guarded
by checking it is not currently referenced by any
role_permission_scopes/user_permission_scopes row (both have
`ondelete="CASCADE"` at the DB level, so an unguarded delete would
silently wipe out every grant of it -- exactly the kind of ad hoc,
uncontrolled removal the model's own docstring warns against).
"""
from app.core.audit_logs.services import write_audit_log
from app.core.authorization.models import RolePermissionScope, ScopeType, UserPermissionScope
from app.core.permissions.models import Permission
from app.core.permissions.schemas import PermissionCreate, PermissionUpdate
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import has_permission
from app.utils.exceptions import ConflictError, NotFoundError
from app.utils.pagination import paginate_query

MODULE = "core"
ENTITY_TYPE = "permission"


def _require(actor: User, action: str) -> None:
    key = f"core.permission.{action}"
    if not has_permission(actor, key, ScopeType.GLOBAL, None):
        raise PermissionDeniedError("permission_denied", f"Missing permission '{key}' for this action.")


def _get_or_404(permission_id: int) -> Permission:
    permission = db.session.get(Permission, permission_id)
    if permission is None:
        raise NotFoundError(f"Permission {permission_id} was not found.")
    return permission


def list_permissions(actor: User, *, page: int, per_page: int):
    _require(actor, "read")
    query = db.session.query(Permission).order_by(Permission.id)
    return paginate_query(query, page, per_page)


def get_permission(actor: User, permission_id: int) -> Permission:
    _require(actor, "read")
    return _get_or_404(permission_id)


def create_permission(actor: User, payload: PermissionCreate, *, ip_address: str | None) -> Permission:
    _require(actor, "create")
    module, resource, action = payload.key.split(".")

    permission = Permission(
        key=payload.key, module=module, resource=resource, action=action,
        is_delegable=payload.is_delegable, description=payload.description,
    )
    db.session.add(permission)
    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("A permission with this key already exists.") from exc

    write_audit_log(
        user_id=actor.id, action="create", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=permission.id, metadata={"key": permission.key}, ip_address=ip_address,
    )
    db.session.commit()
    return permission


def update_permission(
    actor: User, permission_id: int, payload: PermissionUpdate, *, ip_address: str | None
) -> Permission:
    _require(actor, "update")
    permission = _get_or_404(permission_id)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(permission, field, value)

    try:
        db.session.flush()
    except Exception as exc:
        db.session.rollback()
        raise ConflictError("Could not update permission (constraint violation).") from exc

    write_audit_log(
        user_id=actor.id, action="update", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=permission.id, metadata={"changed_fields": list(changes.keys())}, ip_address=ip_address,
    )
    db.session.commit()
    return permission


def delete_permission(actor: User, permission_id: int, *, ip_address: str | None) -> None:
    _require(actor, "delete")
    permission = _get_or_404(permission_id)

    in_use = (
        db.session.query(RolePermissionScope).filter_by(permission_id=permission.id).first()
        or db.session.query(UserPermissionScope).filter_by(permission_id=permission.id).first()
    )
    if in_use is not None:
        raise ConflictError(
            "Cannot delete a permission that is still granted via a role or user scope."
        )

    write_audit_log(
        user_id=actor.id, action="delete", module=MODULE, entity_type=ENTITY_TYPE,
        entity_id=permission.id, metadata={"key": permission.key}, ip_address=ip_address,
    )
    db.session.delete(permission)
    db.session.commit()
