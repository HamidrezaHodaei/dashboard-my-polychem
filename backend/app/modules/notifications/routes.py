"""/api/notifications -- the header bell."""
from flask import Blueprint, g, request
from pydantic import BaseModel, Field

from app.core.auth.decorators import require_authenticated
from app.modules.notifications import services
from app.utils.responses import success_response

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


class MarkRead(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)
    all: bool = False


@bp.get("")
@require_authenticated
def list_notifications():
    limit = min(max(request.args.get("limit", default=30, type=int), 1), 100)
    only_unread = request.args.get("unread", "").lower() in ("1", "true")
    before_id = request.args.get("before_id", default=None, type=int)
    return success_response(
        data=services.list_for(g.current_user.id, limit=limit, only_unread=only_unread, before_id=before_id)
    )


@bp.post("/read")
@require_authenticated
def mark_read():
    payload = MarkRead.model_validate(request.get_json(silent=True) or {})
    count = services.mark_read(g.current_user.id, ids=payload.ids, all_=payload.all)
    return success_response(data={"marked": count})
