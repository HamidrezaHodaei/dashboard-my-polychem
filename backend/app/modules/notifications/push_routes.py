"""/api/push -- device registration for Web Push, test sends and the cron entry point."""
import hmac

from flask import Blueprint, current_app, g, request
from pydantic import BaseModel, Field

from app.core.auth.decorators import require_authenticated
from app.extensions import limiter
from app.modules.notifications import push
from app.utils.exceptions import NotFoundError
from app.utils.responses import error_response, success_response

bp = Blueprint("push", __name__, url_prefix="/api/push")


class SubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=2048)
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=64)
    label: str | None = Field(default=None, max_length=100)


class EndpointIn(BaseModel):
    endpoint: str = Field(max_length=2048)


@bp.get("/config")
@require_authenticated
def config():
    """Whether the server can send pushes, and the public VAPID key the browser subscribes with."""
    configured = push.is_configured()
    return success_response(data={"enabled": configured, "public_key": push.public_key() if configured else None})


@bp.get("/subscriptions")
@require_authenticated
def list_subscriptions():
    return success_response(data={"items": push.list_devices(g.current_user.id, request.args.get("endpoint"))})


@bp.post("/subscriptions")
@require_authenticated
@limiter.limit("60 per hour")
def register_subscription():
    if not push.is_configured():
        return error_response("PUSH_DISABLED", "اعلان فوری در این سرور فعال نشده است.", 503)
    body = SubscriptionIn.model_validate(request.get_json(silent=True) or {})
    sub = push.upsert_subscription(
        g.current_user.id, endpoint=body.endpoint, p256dh=body.p256dh, auth=body.auth,
        user_agent=request.headers.get("User-Agent"), label=body.label,
    )
    return success_response(data=push.device_dict(sub, sub.endpoint_hash), status_code=201)


@bp.post("/subscriptions/detach")
@require_authenticated
def detach_subscription():
    """Used at sign-out and when the user switches push off on this browser."""
    body = EndpointIn.model_validate(request.get_json(silent=True) or {})
    return success_response(data={"removed": push.detach_endpoint(g.current_user.id, body.endpoint)})


@bp.delete("/subscriptions/<int:sub_id>")
@require_authenticated
def delete_subscription(sub_id: int):
    if not push.remove_device(g.current_user.id, sub_id):
        raise NotFoundError("دستگاه پیدا نشد.")
    return success_response(data={"removed": True})


@bp.post("/subscriptions/<int:sub_id>/test")
@require_authenticated
@limiter.limit("20 per hour")
def test_subscription(sub_id: int):
    return success_response(data=push.send_test(g.current_user.id, sub_id))


@bp.post("/cron")
@limiter.limit("120 per hour")
def cron():
    """For hosts without shell cron: `curl -X POST -H "X-Cron-Token: ..." https://api.../api/push/cron`.
    Disabled unless PUSH_CRON_TOKEN is set; the comparison is constant-time."""
    token = current_app.config.get("PUSH_CRON_TOKEN") or ""
    given = request.headers.get("X-Cron-Token", "")
    if not token or not hmac.compare_digest(token.encode(), given.encode()):
        return error_response("NOT_FOUND", "Not found.", 404)  # do not reveal that the endpoint exists
    if not push.is_configured():
        return success_response(data={"skipped": "not_configured"})
    return success_response(data=push.tick())
