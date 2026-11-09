"""GET/POST/PATCH/DELETE /api/core/organizations -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.organizations import services
from app.core.organizations.schemas import OrganizationCreate, OrganizationPublic, OrganizationUpdate
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("organizations", __name__, url_prefix="/api/core/organizations")


def _dump(org) -> dict:
    return OrganizationPublic.model_validate(org).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_organizations():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_organizations(g.current_user, page=page, per_page=per_page)
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/<int:organization_id>")
@require_authenticated
def get_organization(organization_id: int):
    org = services.get_organization(g.current_user, organization_id)
    return success_response(data=_dump(org))


@bp.post("")
@require_authenticated
def create_organization():
    payload = OrganizationCreate.model_validate(request.get_json(silent=True) or {})
    org = services.create_organization(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(org), status_code=201)


@bp.patch("/<int:organization_id>")
@require_authenticated
def update_organization(organization_id: int):
    payload = OrganizationUpdate.model_validate(request.get_json(silent=True) or {})
    org = services.update_organization(
        g.current_user, organization_id, payload, ip_address=request.remote_addr
    )
    return success_response(data=_dump(org))


@bp.delete("/<int:organization_id>")
@require_authenticated
def delete_organization(organization_id: int):
    services.delete_organization(g.current_user, organization_id, ip_address=request.remote_addr)
    return success_response(data={})
