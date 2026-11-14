"""
/api/crm/request-samples -- Request Sample module. Every route requires authentication; the
`crm.request_sample.*` permissions are enforced in services.py. Static paths are declared before
`/<int:id>`. The table, KPI cards and every chart share ONE filter parser (services.parse_filters).
"""
from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.core.export_files import collect_pages, send_export
from app.modules import export_rows
from app.modules.request_samples import files, services
from app.modules.request_samples.schemas import (
    ConvertIn, DeliveryIn, DispatchIn, FeedbackIn, FollowUpIn, RequestIn, TransitionIn,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("request_samples", __name__, url_prefix="/api/crm/request-samples")


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _detail(req) -> dict:
    return services.dump(req, g.current_user, detail=True)


# ── pickers / analytics / list ───────────────────────────────────────
@bp.get("/options")
@require_authenticated
def options():
    return success_response(data=services.options(g.current_user))


@bp.get("/option-items")
@require_authenticated
def option_items():
    return success_response(data=services.product_options(g.current_user))


@bp.get("/reps")
@require_authenticated
def reps():
    return success_response(data=services.rep_candidates(g.current_user))


@bp.get("/analytics")
@require_authenticated
def analytics():
    f = services.parse_filters(request.args)
    top = max(3, min(request.args.get("top", 8, type=int), 20))
    return success_response(data=services.analytics(
        g.current_user, f, granularity=request.args.get("granularity", "month"), top=top,
    ))


@bp.get("")
@require_authenticated
def list_requests():
    page, per_page = parse_pagination(request.args)
    f = services.parse_filters(request.args)
    items, total = services.list_requests(g.current_user, f, page=page, per_page=per_page, sort=request.args.get("sort", "-id"))
    return success_response(
        data=[services.dump(i, g.current_user) for i in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/export")
@require_authenticated
def export_requests():
    """Excel / Word of the requests matching the filters (`crm.request_sample.export`)."""
    export_rows.require_export(g.current_user, "crm.request_sample.export")
    f = services.parse_filters(request.args)
    rows = [services.dump(r, g.current_user) for r in services.all_requests(g.current_user, f)]
    title, headers, data = export_rows.request_samples_table(rows)
    return send_export(request.args.get("format", "xlsx"), title=title, filename="request-samples", headers=headers, rows=data)


@bp.post("")
@require_authenticated
def create_request():
    payload = RequestIn.model_validate(_json())
    req = services.create_request(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_detail(req), status_code=201)


# ── files (declared before /<int:id>) ────────────────────────────────
@bp.post("/files")
@require_authenticated
def upload_file():
    kind = (request.form.get("kind") or "OTHER").upper()
    return success_response(data=services.upload_orphan(g.current_user, request.files.get("file"), kind), status_code=201)


@bp.get("/files/<file_id>")
@require_authenticated
def download_file(file_id: str):
    row = services.download_file(g.current_user, file_id)
    response = send_file(files.disk_path(row), as_attachment=True, download_name=row.original_name,
                         mimetype=row.content_type or "application/octet-stream")
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.delete("/files/<file_id>")
@require_authenticated
def delete_file(file_id: str):
    services.delete_file(g.current_user, file_id, request.remote_addr)
    return success_response(data={"deleted": True})


# ── one request ──────────────────────────────────────────────────────
@bp.get("/<int:request_id>")
@require_authenticated
def get_request(request_id: int):
    return success_response(data=_detail(services.get_visible(g.current_user, request_id)))


@bp.put("/<int:request_id>")
@require_authenticated
def update_request(request_id: int):
    payload = RequestIn.model_validate(_json())
    return success_response(data=_detail(services.update_request(g.current_user, request_id, payload, ip_address=request.remote_addr)))


@bp.delete("/<int:request_id>")
@require_authenticated
def delete_request(request_id: int):
    services.delete_request(g.current_user, request_id, ip_address=request.remote_addr)
    return success_response(data={"deleted": True})


@bp.post("/<int:request_id>/transition")
@require_authenticated
def transition(request_id: int):
    payload = TransitionIn.model_validate(_json())
    return success_response(data=_detail(services.transition(g.current_user, request_id, payload, ip_address=request.remote_addr)))


@bp.post("/<int:request_id>/new-request")
@require_authenticated
def new_request(request_id: int):
    req = services.new_request_from(g.current_user, request_id, ip_address=request.remote_addr)
    return success_response(data=_detail(req), status_code=201)


@bp.post("/<int:request_id>/files")
@require_authenticated
def upload_to_request(request_id: int):
    kind = (request.form.get("kind") or "OTHER").upper()
    data = services.upload_to_request(g.current_user, request_id, request.files.get("file"), kind, request.remote_addr)
    return success_response(data=data, status_code=201)


@bp.post("/<int:request_id>/dispatches")
@require_authenticated
def add_dispatch(request_id: int):
    payload = DispatchIn.model_validate(_json())
    req = services.add_dispatch(g.current_user, request_id, payload, ip_address=request.remote_addr)
    return success_response(data=_detail(req), status_code=201)


@bp.delete("/<int:request_id>/dispatches/<int:dispatch_id>")
@require_authenticated
def delete_dispatch(request_id: int, dispatch_id: int):
    req = services.delete_dispatch(g.current_user, request_id, dispatch_id, ip_address=request.remote_addr)
    return success_response(data=_detail(req))


@bp.post("/<int:request_id>/delivery")
@require_authenticated
def confirm_delivery(request_id: int):
    """The customer received the sample (ارسال‌شده -> تحویل شد)."""
    payload = DeliveryIn.model_validate(_json())
    return success_response(data=_detail(services.confirm_delivery(g.current_user, request_id, payload, ip_address=request.remote_addr)))


@bp.post("/<int:request_id>/followups")
@require_authenticated
def add_followup(request_id: int):
    payload = FollowUpIn.model_validate(_json())
    req = services.add_followup(g.current_user, request_id, payload, ip_address=request.remote_addr)
    return success_response(data=_detail(req), status_code=201)


@bp.put("/<int:request_id>/followups/<int:followup_id>")
@require_authenticated
def update_followup(request_id: int, followup_id: int):
    payload = FollowUpIn.model_validate(_json())
    req = services.update_followup(g.current_user, request_id, followup_id, payload, ip_address=request.remote_addr)
    return success_response(data=_detail(req))


@bp.delete("/<int:request_id>/followups/<int:followup_id>")
@require_authenticated
def delete_followup(request_id: int, followup_id: int):
    req = services.delete_followup(g.current_user, request_id, followup_id, ip_address=request.remote_addr)
    return success_response(data=_detail(req))


@bp.put("/<int:request_id>/feedback")
@require_authenticated
def set_feedback(request_id: int):
    payload = FeedbackIn.model_validate(_json())
    return success_response(data=_detail(services.set_feedback(g.current_user, request_id, payload, ip_address=request.remote_addr)))


@bp.post("/<int:request_id>/convert")
@require_authenticated
def convert(request_id: int):
    payload = ConvertIn.model_validate(_json())
    req = services.convert_to_sales(g.current_user, request_id, payload.sale_id, payload.note, ip_address=request.remote_addr)
    return success_response(data=_detail(req))
