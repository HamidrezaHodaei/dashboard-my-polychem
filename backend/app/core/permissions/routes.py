"""GET/POST/PATCH/DELETE /api/core/permissions -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.permissions import services
from app.core.permissions.schemas import PermissionCreate, PermissionPublic, PermissionUpdate
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("permissions", __name__, url_prefix="/api/core/permissions")


def _dump(permission) -> dict:
    return PermissionPublic.model_validate(permission).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_permissions():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_permissions(g.current_user, page=page, per_page=per_page)
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/<int:permission_id>")
@require_authenticated
def get_permission(permission_id: int):
    permission = services.get_permission(g.current_user, permission_id)
    return success_response(data=_dump(permission))


@bp.post("")
@require_authenticated
def create_permission():
    payload = PermissionCreate.model_validate(request.get_json(silent=True) or {})
    permission = services.create_permission(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(permission), status_code=201)


@bp.patch("/<int:permission_id>")
@require_authenticated
def update_permission(permission_id: int):
    payload = PermissionUpdate.model_validate(request.get_json(silent=True) or {})
    permission = services.update_permission(
        g.current_user, permission_id, payload, ip_address=request.remote_addr
    )
    return success_response(data=_dump(permission))


@bp.delete("/<int:permission_id>")
@require_authenticated
def delete_permission(permission_id: int):
    services.delete_permission(g.current_user, permission_id, ip_address=request.remote_addr)
    return success_response(data={})
