"""/api/notifications -- the header bell."""
from flask import Blueprint, g, request
from pydantic import BaseModel, Field

from app.core.auth.decorators import require_authenticated
from app.modules.notifications import push, services
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
    read = request.args.get("read", "").lower()
    return success_response(
        data=services.list_for(
            g.current_user.id, limit=limit, only_unread=only_unread, before_id=before_id,
            q=request.args.get("q"), category=request.args.get("category") or None,
            read=read if read in ("all", "read", "unread") else None,
        )
    )


@bp.post("/read")
@require_authenticated
def mark_read():
    payload = MarkRead.model_validate(request.get_json(silent=True) or {})
    count = services.mark_read(g.current_user.id, ids=payload.ids, all_=payload.all)
    return success_response(data={"marked": count})


class PreferencesIn(BaseModel):
    push_enabled: bool = True
    show_preview: bool = True
    quiet_enabled: bool = False
    quiet_start: str = Field(default="22:00", max_length=5)
    quiet_end: str = Field(default="07:00", max_length=5)
    categories: dict[str, bool] = Field(default_factory=dict)


@bp.get("/preferences")
@require_authenticated
def get_preferences():
    return success_response(data=push.preferences_for(g.current_user.id))


@bp.put("/preferences")
@require_authenticated
def put_preferences():
    body = PreferencesIn.model_validate(request.get_json(silent=True) or {})
    push.save_settings(g.current_user.id, **body.model_dump())
    return success_response(data=push.preferences_for(g.current_user.id))
