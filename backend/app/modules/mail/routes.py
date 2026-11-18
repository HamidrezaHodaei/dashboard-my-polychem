"""
/api/mail -- organizational correspondence (مکاتبات). Every route requires authentication; the
`correspondence.mail.*` permissions (or an enabled organizational unit) are enforced in services.py.
Conversations are addressed by the id of any message in them (the id the list returns).
"""
from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.modules.mail import files, services
from app.modules.mail.schemas import ComposeIn, FlagsIn, LabelsIn, MoveIn, ReplyIn, UnitAccessIn
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("mail", __name__, url_prefix="/api/mail")


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _flag(name: str) -> bool:
    return request.args.get(name, "").lower() in ("1", "true", "yes")


# ── sidebar / pickers ────────────────────────────────────────────────
@bp.get("/meta")
@require_authenticated
def meta():
    return success_response(data=services.meta(g.current_user))


@bp.get("/counters")
@require_authenticated
def counters():
    return success_response(data=services.counters(g.current_user))


@bp.get("/recipients")
@require_authenticated
def recipients():
    exclude = [int(x) for x in (request.args.get("exclude") or "").split(",") if x.strip().isdigit()][:500]
    data = services.search_recipients(
        g.current_user, request.args.get("q"), limit=request.args.get("limit", 20, type=int), exclude=exclude,
    )
    return success_response(data=data)


# ── lists / one conversation ─────────────────────────────────────────
@bp.get("/threads")
@require_authenticated
def list_threads():
    page, per_page = parse_pagination(request.args)
    label = request.args.get("label") or None
    folder = request.args.get("folder") or (None if label or _flag("starred") else "inbox")
    items, total, people = services.list_threads(
        g.current_user, folder_slug=folder, label=label, q=request.args.get("q"),
        unread=_flag("unread"), starred=_flag("starred"), sort=request.args.get("sort", "newest"),
        page=page, per_page=per_page,
    )
    return success_response(
        data={"items": items, "people": people, "total": total}, meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/messages/<int:message_id>/thread")
@require_authenticated
def get_thread(message_id: int):
    return success_response(data=services.get_thread(g.current_user, message_id))


# ── composing ────────────────────────────────────────────────────────
@bp.post("/messages")
@require_authenticated
def send_message():
    payload = ComposeIn.model_validate(_json())
    return success_response(data=services.send(g.current_user, payload, None, request.remote_addr), status_code=201)


@bp.post("/messages/<int:message_id>/reply")
@require_authenticated
def reply(message_id: int):
    payload = ReplyIn.model_validate(_json())
    return success_response(data=services.reply(g.current_user, message_id, payload, request.remote_addr), status_code=201)


@bp.post("/drafts")
@require_authenticated
def create_draft():
    payload = ComposeIn.model_validate(_json())
    return success_response(data=services.save_draft(g.current_user, payload, None, request.remote_addr), status_code=201)


@bp.put("/drafts/<int:draft_id>")
@require_authenticated
def update_draft(draft_id: int):
    payload = ComposeIn.model_validate(_json())
    return success_response(data=services.save_draft(g.current_user, payload, draft_id, request.remote_addr))


@bp.post("/drafts/<int:draft_id>/send")
@require_authenticated
def send_draft(draft_id: int):
    payload = ComposeIn.model_validate(_json())
    return success_response(data=services.send(g.current_user, payload, draft_id, request.remote_addr))


@bp.delete("/drafts/<int:draft_id>")
@require_authenticated
def discard_draft(draft_id: int):
    services.discard_draft(g.current_user, draft_id, request.remote_addr)
    return success_response(data={"deleted": True})


# ── per-user state of a conversation ─────────────────────────────────
@bp.post("/messages/<int:message_id>/move")
@require_authenticated
def move(message_id: int):
    payload = MoveIn.model_validate(_json())
    return success_response(data=services.move_thread(g.current_user, message_id, payload.folder, request.remote_addr))


@bp.patch("/messages/<int:message_id>/flags")
@require_authenticated
def flags(message_id: int):
    payload = FlagsIn.model_validate(_json())
    return success_response(data=services.set_flags(g.current_user, message_id, payload))


@bp.put("/messages/<int:message_id>/labels")
@require_authenticated
def labels(message_id: int):
    payload = LabelsIn.model_validate(_json())
    return success_response(data=services.set_labels(g.current_user, message_id, payload))


@bp.delete("/messages/<int:message_id>")
@require_authenticated
def delete_permanently(message_id: int):
    services.delete_thread_permanently(g.current_user, message_id, request.remote_addr)
    return success_response(data={"deleted": True})


# ── attachments ──────────────────────────────────────────────────────
@bp.post("/attachments")
@require_authenticated
def upload_attachment():
    return success_response(data=services.upload_attachment(g.current_user, request.files.get("file")), status_code=201)


@bp.get("/attachments/<file_id>")
@require_authenticated
def download_attachment(file_id: str):
    row = services.download_attachment(g.current_user, file_id)
    response = send_file(
        files.disk_path(row), as_attachment=True, download_name=row.original_name,
        mimetype=row.content_type or "application/octet-stream",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.delete("/attachments/<file_id>")
@require_authenticated
def delete_attachment(file_id: str):
    services.delete_attachment(g.current_user, file_id)
    return success_response(data={"deleted": True})


# ── which organizational units may use mail ──────────────────────────
@bp.get("/access/units")
@require_authenticated
def list_units():
    return success_response(data=services.list_units(g.current_user))


@bp.put("/access/units")
@require_authenticated
def set_units():
    payload = UnitAccessIn.model_validate(_json())
    return success_response(data=services.set_units(g.current_user, payload, request.remote_addr))
