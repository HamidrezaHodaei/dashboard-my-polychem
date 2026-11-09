"""POST/GET /api/authz/delegations -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.authorization import services
from app.core.authorization.schemas import DelegationCreate, DelegationPublic
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("delegations", __name__, url_prefix="/api/authz/delegations")


def _dump(delegation) -> dict:
    return DelegationPublic.model_validate(delegation).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_delegations():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_my_delegations(g.current_user, page=page, per_page=per_page)
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.post("")
@require_authenticated
def create_delegation():
    payload = DelegationCreate.model_validate(request.get_json(silent=True) or {})
    delegation = services.create_delegation(
        g.current_user,
        delegatee_user_id=payload.delegatee_user_id,
        permission_key=payload.permission_key,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
    )
    return success_response(data=_dump(delegation), status_code=201)


@bp.post("/<int:delegation_id>/revoke")
@require_authenticated
def revoke_delegation(delegation_id: int):
    delegation = services.revoke_delegation(g.current_user, delegation_id)
    return success_response(data=_dump(delegation))
