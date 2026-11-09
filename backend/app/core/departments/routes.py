"""GET/POST/PATCH/DELETE /api/core/departments -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.departments import services
from app.core.departments.schemas import DepartmentCreate, DepartmentPublic, DepartmentUpdate
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("departments", __name__, url_prefix="/api/core/departments")


def _dump(dept) -> dict:
    return DepartmentPublic.model_validate(dept).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_departments():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_departments(g.current_user, page=page, per_page=per_page)
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/<int:department_id>")
@require_authenticated
def get_department(department_id: int):
    dept = services.get_department(g.current_user, department_id)
    return success_response(data=_dump(dept))


@bp.post("")
@require_authenticated
def create_department():
    payload = DepartmentCreate.model_validate(request.get_json(silent=True) or {})
    dept = services.create_department(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(dept), status_code=201)


@bp.patch("/<int:department_id>")
@require_authenticated
def update_department(department_id: int):
    payload = DepartmentUpdate.model_validate(request.get_json(silent=True) or {})
    dept = services.update_department(
        g.current_user, department_id, payload, ip_address=request.remote_addr
    )
    return success_response(data=_dump(dept))


@bp.delete("/<int:department_id>")
@require_authenticated
def delete_department(department_id: int):
    services.delete_department(g.current_user, department_id, ip_address=request.remote_addr)
    return success_response(data={})
