"""GET/POST/PATCH/DELETE /api/core/teams (+ nested /members) -- Phase 4."""
from flask import Blueprint, g, request

from app.core.auth.decorators import require_authenticated
from app.core.teams import services
from app.core.teams.schemas import TeamCreate, TeamMemberAdd, TeamMemberPublic, TeamPublic, TeamUpdate
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("teams", __name__, url_prefix="/api/core/teams")


def _dump(team) -> dict:
    return TeamPublic.model_validate(team).model_dump(mode="json")


def _dump_member(member) -> dict:
    return TeamMemberPublic.model_validate(member).model_dump(mode="json")


@bp.get("")
@require_authenticated
def list_teams():
    page, per_page = parse_pagination(request.args)
    items, total = services.list_teams(g.current_user, page=page, per_page=per_page)
    return success_response(
        data=[_dump(item) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/<int:team_id>")
@require_authenticated
def get_team(team_id: int):
    team = services.get_team(g.current_user, team_id)
    return success_response(data=_dump(team))


@bp.post("")
@require_authenticated
def create_team():
    payload = TeamCreate.model_validate(request.get_json(silent=True) or {})
    team = services.create_team(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(team), status_code=201)


@bp.patch("/<int:team_id>")
@require_authenticated
def update_team(team_id: int):
    payload = TeamUpdate.model_validate(request.get_json(silent=True) or {})
    team = services.update_team(g.current_user, team_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(team))


@bp.delete("/<int:team_id>")
@require_authenticated
def delete_team(team_id: int):
    services.delete_team(g.current_user, team_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/<int:team_id>/members")
@require_authenticated
def list_team_members(team_id: int):
    members = services.list_team_members(g.current_user, team_id)
    return success_response(data=[_dump_member(m) for m in members])


@bp.post("/<int:team_id>/members")
@require_authenticated
def add_team_member(team_id: int):
    payload = TeamMemberAdd.model_validate(request.get_json(silent=True) or {})
    member = services.add_team_member(
        g.current_user, team_id, payload.user_id, ip_address=request.remote_addr
    )
    return success_response(data=_dump_member(member), status_code=201)


@bp.delete("/<int:team_id>/members/<int:user_id>")
@require_authenticated
def remove_team_member(team_id: int, user_id: int):
    services.remove_team_member(g.current_user, team_id, user_id, ip_address=request.remote_addr)
    return success_response(data={})
