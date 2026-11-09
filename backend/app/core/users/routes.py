"""GET/POST/PATCH/DELETE /api/core/users (+ nested /roles) -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.users import services
from app.core.users.schemas import (
    PermissionMatrixUpdate,
    UserCreate,
    UserPasswordSet,
    UserPublic,
    UserRoleAssign,
    UserRolePublic,
    UserUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("users", __name__, url_prefix="/api/core/users")


def _dump(user) -> dict:
    return UserPublic.model_validate(user).model_dump(mode="json")


def _dump_role(user_role) -> dict:
    return UserRolePublic.model_validate(user_role).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_users():
    page, per_page = parse_pagination(request.args)
    include_inactive = request.args.get("include_inactive", "").lower() in ("1", "true", "yes")
    items, total = services.list_users(
        g.current_user, page=page, per_page=per_page,
        include_inactive=include_inactive, search=request.args.get("q"),
    )
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.post("/<int:user_id>/password")
@require_authenticated
def set_user_password(user_id: int):
    payload = UserPasswordSet.model_validate(request.get_json(silent=True) or {})
    services.set_user_password(g.current_user, user_id, payload.new_password, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:user_id>")
@require_authenticated
def get_user(user_id: int):
    user = services.get_user(g.current_user, user_id)
    return success_response(data=_dump(user))


@bp.post("")
@require_authenticated
def create_user():
    payload = UserCreate.model_validate(request.get_json(silent=True) or {})
    user = services.create_user(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(user), status_code=201)


@bp.patch("/<int:user_id>")
@require_authenticated
def update_user(user_id: int):
    payload = UserUpdate.model_validate(request.get_json(silent=True) or {})
    user = services.update_user(g.current_user, user_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(user))


@bp.delete("/<int:user_id>")
@require_authenticated
def delete_user(user_id: int):
    services.delete_user(g.current_user, user_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:user_id>/roles")
@require_authenticated
def list_user_roles(user_id: int):
    user_roles = services.list_user_roles(g.current_user, user_id)
    return success_response(data=[_dump_role(ur) for ur in user_roles])


@bp.post("/<int:user_id>/roles")
@require_authenticated
def assign_role(user_id: int):
    payload = UserRoleAssign.model_validate(request.get_json(silent=True) or {})
    user_role = services.assign_role(
        g.current_user, user_id, payload.role_id, payload.organization_id,
        ip_address=request.remote_addr,
    )
    return success_response(data=_dump_role(user_role), status_code=201)


@bp.delete("/<int:user_id>/roles/<int:role_id>")
@require_authenticated
def revoke_role(user_id: int, role_id: int):
    services.revoke_role(g.current_user, user_id, role_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:user_id>/access")
@require_authenticated
def get_user_access(user_id: int):
    """Roles, role-sourced grants, direct grants and the merged effective permissions."""
    return success_response(data=services.get_access_summary(g.current_user, user_id))


@bp.get("/<int:user_id>/permission-matrix")
@require_authenticated
def get_user_permission_matrix(user_id: int):
    return success_response(data=services.get_permission_matrix(g.current_user, user_id))


@bp.put("/<int:user_id>/permission-matrix")
@require_authenticated
def set_user_permission_matrix(user_id: int):
    payload = PermissionMatrixUpdate.model_validate(request.get_json(silent=True) or {})
    data = services.set_permission_matrix(
        g.current_user, user_id, payload.cells, ip_address=request.remote_addr
    )
    return success_response(data=data)
