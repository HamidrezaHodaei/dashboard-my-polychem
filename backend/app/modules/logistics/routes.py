"""
/api/logistics -- transport-company / driver registration + staff management.

PUBLIC (no auth, rate-limited -- what the registration wizard calls):
    GET  /public/wizard         step/field/condition definition per applicant type
    GET  /public/reference      provinces+cities, vehicle/body/cargo types, countries, permits
    POST /public/validate-step  validate one wizard step, returns normalised data
    POST /public/files          upload a permit scan -> {id, name, size}
    POST /public/register       final submit (lands as PENDING)

STAFF (JWT + per-type permission, see services.py):
    GET    /applicants            list (only the types the caller may read)
    POST   /applicants            add by hand
    GET    /applicants/<id>
    PATCH  /applicants/<id>       replace one or more sections
    POST   /applicants/<id>/review   approve / reject / suspend / reopen
    DELETE /applicants/<id>       soft delete
    GET    /stats
    GET    /files/<id>            download an uploaded permit
"""
from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.extensions import limiter
from app.modules.logistics import files, services
from app.modules.logistics.schemas import ChangeRequestIn, ReviewIn, UpdateIn, ValidateStepIn, serialize_applicant
from app.modules.logistics.wizard import WIZARD
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("logistics", __name__, url_prefix="/api/logistics")


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _with_flags(a, *, detail: bool = True) -> dict:
    """The record + what the CURRENT user may do with it (edit / submit / ask for a change / review)."""
    data = serialize_applicant(a, detail=detail)
    data["my_actions"] = services.viewer_flags(g.current_user, a)
    return data


# ── public ───────────────────────────────────────────────────────────
@bp.get("/public/wizard")
@limiter.limit("300 per hour")
def public_wizard():
    return success_response(data=WIZARD)


@bp.get("/public/reference")
@limiter.limit("300 per hour")
def public_reference():
    return success_response(data=services.catalog())


@bp.post("/public/validate-step")
@limiter.limit("240 per hour")
def public_validate_step():
    body = ValidateStepIn.model_validate(_json())
    return success_response(data=services.validate_public_step(body.applicant_type, body.step, body.data))


@bp.post("/public/files")
@limiter.limit("40 per hour")
def public_upload():
    row = files.save_upload(request.files.get("file"), uploaded_by_user_id=None)
    return success_response(data=files.file_ref(row), status_code=201)


@bp.post("/public/register")
@limiter.limit("20 per hour")
def public_register():
    a = services.register_public(_json(), ip_address=request.remote_addr)
    return success_response(
        data={"id": a.id, "applicant_type": a.applicant_type.value, "status": a.status.value,
              "display_name": a.display_name},
        status_code=201,
    )


# ── staff ────────────────────────────────────────────────────────────
@bp.get("/applicants")
@require_authenticated
def list_applicants():
    page, per_page = parse_pagination(request.args)
    a = request.args
    items, total = services.list_applicants(
        g.current_user, page=page, per_page=per_page,
        applicant_type=a.get("applicant_type", ""), search=a.get("search", ""), status=a.get("status", ""),
        province=a.get("province", ""), area_type=a.get("area_type", ""),
        vehicle_type=a.get("vehicle_type", ""), body_type=a.get("body_type", ""),
        include_inactive=a.get("include_inactive", "").lower() == "true",
    )
    return success_response(
        data=[_with_flags(i, detail=False) for i in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/stats")
@require_authenticated
def stats():
    return success_response(data=services.stats(g.current_user))


@bp.get("/applicants/<int:applicant_id>")
@require_authenticated
def get_applicant(applicant_id: int):
    return success_response(data=_with_flags(services.get_applicant(g.current_user, applicant_id)))


@bp.post("/applicants")
@require_authenticated
def create_applicant():
    a = services.create_admin(g.current_user, _json(), ip_address=request.remote_addr)
    return success_response(data=_with_flags(a), status_code=201)


@bp.patch("/applicants/<int:applicant_id>")
@require_authenticated
def update_applicant(applicant_id: int):
    payload = UpdateIn.model_validate(_json())
    a = services.update_applicant(g.current_user, applicant_id, payload, ip_address=request.remote_addr)
    return success_response(data=_with_flags(a))


@bp.post("/applicants/<int:applicant_id>/review")
@require_authenticated
def review_applicant(applicant_id: int):
    payload = ReviewIn.model_validate(_json())
    a = services.review_applicant(g.current_user, applicant_id, payload, ip_address=request.remote_addr)
    return success_response(data=_with_flags(a))


@bp.post("/applicants/<int:applicant_id>/finalize")
@require_authenticated
def finalize_applicant(applicant_id: int):
    a = services.finalize_applicant(g.current_user, applicant_id, ip_address=request.remote_addr)
    return success_response(data=_with_flags(a))


@bp.post("/applicants/<int:applicant_id>/request-change")
@require_authenticated
def request_change(applicant_id: int):
    payload = ChangeRequestIn.model_validate(request.get_json(silent=True) or {})
    a = services.request_change(g.current_user, applicant_id, payload, ip_address=request.remote_addr)
    return success_response(data=_with_flags(a))


@bp.delete("/applicants/<int:applicant_id>")
@require_authenticated
def delete_applicant(applicant_id: int):
    services.delete_applicant(g.current_user, applicant_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/files/<file_id>")
@require_authenticated
def download_file(file_id: str):
    services.require_file_read(g.current_user)
    row = files.get_file_or_404(file_id)
    response = send_file(
        files.disk_path(row), as_attachment=True, download_name=row.original_name,
        mimetype=row.content_type or "application/octet-stream",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
