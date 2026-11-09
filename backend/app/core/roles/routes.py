"""GET/POST/PATCH/DELETE /api/core/roles -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.roles import services
from app.core.roles.schemas import (
    RoleCreate,
    RolePermissionMatrixUpdate,
    RolePermissionGrantCreate,
    RolePermissionGrantPublic,
    RolePublic,
    RoleUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("roles", __name__, url_prefix="/api/core/roles")


def _dump(role) -> dict:
    return RolePublic.model_validate(role).model_dump(mode="json")


def _dump_grant(grant) -> dict:
    return RolePermissionGrantPublic.model_validate(grant).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_roles():
    page, per_page = parse_pagination(request.args)
    include_inactive = request.args.get("include_inactive", "").lower() in ("1", "true", "yes")
    items, total = services.list_roles(
        g.current_user, page=page, per_page=per_page, include_inactive=include_inactive
    )
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/<int:role_id>")
@require_authenticated
def get_role(role_id: int):
    role = services.get_role(g.current_user, role_id)
    return success_response(data=_dump(role))


@bp.post("")
@require_authenticated
def create_role():
    payload = RoleCreate.model_validate(request.get_json(silent=True) or {})
    role = services.create_role(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(role), status_code=201)


@bp.patch("/<int:role_id>")
@require_authenticated
def update_role(role_id: int):
    payload = RoleUpdate.model_validate(request.get_json(silent=True) or {})
    role = services.update_role(g.current_user, role_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(role))


@bp.delete("/<int:role_id>")
@require_authenticated
def delete_role(role_id: int):
    services.delete_role(g.current_user, role_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:role_id>/permissions")
@require_authenticated
def list_role_permissions(role_id: int):
    grants = services.list_role_permissions(g.current_user, role_id)
    return success_response(data=[_dump_grant(grant) for grant in grants])


@bp.post("/<int:role_id>/permissions")
@require_authenticated
def grant_role_permission(role_id: int):
    payload = RolePermissionGrantCreate.model_validate(request.get_json(silent=True) or {})
    grant = services.grant_permission_to_role(
        g.current_user, role_id, payload, ip_address=request.remote_addr
    )
    return success_response(data=_dump_grant(grant), status_code=201)


@bp.delete("/<int:role_id>/permissions/<int:grant_id>")
@require_authenticated
def revoke_role_permission(role_id: int, grant_id: int):
    services.revoke_permission_from_role(g.current_user, role_id, grant_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:role_id>/permission-matrix")
@require_authenticated
def get_role_permission_matrix(role_id: int):
    return success_response(data=services.get_permission_matrix(g.current_user, role_id))


@bp.put("/<int:role_id>/permission-matrix")
@require_authenticated
def set_role_permission_matrix(role_id: int):
    payload = RolePermissionMatrixUpdate.model_validate(request.get_json(silent=True) or {})
    data = services.set_permission_matrix(
        g.current_user, role_id, payload.cells, ip_address=request.remote_addr
    )
    return success_response(data=data)
