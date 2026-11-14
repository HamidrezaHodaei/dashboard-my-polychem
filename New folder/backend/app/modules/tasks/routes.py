"""GET/POST/PATCH/DELETE /api/tasks -- Phase 4a. API.md §4: resource-oriented, `/api/<module>/<resource>`."""
from flask import Blueprint, g, request, send_file

from app.core.auth.decorators import require_authenticated
from app.modules.tasks import branding
from app.modules.tasks import rules as task_rules
from app.modules.tasks import services
from app.modules.tasks.models import TaskStatus
from app.modules.tasks.schemas import (
    AssignmentRuleCreate,
    ChecklistCreate,
    ChecklistUpdate,
    NoteCreate,
    TaskAnalytics,
    TaskAssign,
    TaskAssigneesSet,
    TaskAssignmentPublic,
    TaskRefer,
    TaskCreate,
    TaskPublic,
    TaskUpdate,
)
from app.utils.pagination import parse_pagination
from app.utils.responses import success_response

bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


def _dump(task, can_manage: bool | None = None) -> dict:
    data = TaskPublic.model_validate(task).model_dump(mode="json")
    data["can_manage"] = (
        services.can_manage_flags(g.current_user, [task])[task.id] if can_manage is None else can_manage
    )
    return data


@bp.get("")
@require_authenticated
def list_tasks():
    page, per_page = parse_pagination(request.args)
    status_param = request.args.get("status")
    status = None
    if status_param:
        try:
            status = TaskStatus(status_param)
        except ValueError:
            status = None  # unrecognized filter value is ignored, not a 400 (API.md §4: pagination/filters are a convenience)

    items, total = services.list_tasks(g.current_user, page=page, per_page=per_page, status=status)
    flags = services.can_manage_flags(g.current_user, list(items))
    return success_response(
        data=[_dump(item, flags[item.id]) for item in items],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@bp.get("/meta")
@require_authenticated
def meta():
    return success_response(data=services.task_meta(g.current_user))


@bp.get("/mentions")
@require_authenticated
def my_mentions():
    return success_response(data=services.my_mentions(g.current_user))


@bp.get("/assignment-rules")
@require_authenticated
def list_assignment_rules():
    return success_response(data=task_rules.list_rules(g.current_user))


@bp.post("/assignment-rules")
@require_authenticated
def create_assignment_rule():
    payload = AssignmentRuleCreate.model_validate(request.get_json(silent=True) or {})
    data = task_rules.create_rule(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=data, status_code=201)


@bp.delete("/assignment-rules/<int:rule_id>")
@require_authenticated
def delete_assignment_rule(rule_id: int):
    task_rules.delete_rule(g.current_user, rule_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.get("/analytics")
@require_authenticated
def analytics():
    result = services.task_analytics(g.current_user)
    return success_response(data=TaskAnalytics(**result).model_dump())


@bp.get("/<int:task_id>")
@require_authenticated
def get_task(task_id: int):
    task = services.get_task(g.current_user, task_id)
    return success_response(data=_dump(task))


@bp.post("")
@require_authenticated
def create_task():
    payload = TaskCreate.model_validate(request.get_json(silent=True) or {})
    task = services.create_task(g.current_user, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(task), status_code=201)


@bp.patch("/<int:task_id>")
@require_authenticated
def update_task(task_id: int):
    payload = TaskUpdate.model_validate(request.get_json(silent=True) or {})
    task = services.update_task(g.current_user, task_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(task))


@bp.delete("/<int:task_id>")
@require_authenticated
def delete_task(task_id: int):
    services.delete_task(g.current_user, task_id, ip_address=request.remote_addr)
    return success_response(data={})


@bp.post("/<int:task_id>/assign")
@require_authenticated
def assign_task(task_id: int):
    payload = TaskAssign.model_validate(request.get_json(silent=True) or {})
    assignment = services.assign_task(
        g.current_user, task_id, payload.assignee_user_id, ip_address=request.remote_addr
    )
    return success_response(
        data=TaskAssignmentPublic.model_validate(assignment).model_dump(mode="json"),
        status_code=201,
    )


@bp.put("/<int:task_id>/assignees")
@require_authenticated
def set_assignees(task_id: int):
    payload = TaskAssigneesSet.model_validate(request.get_json(silent=True) or {})
    task = services.set_assignees(g.current_user, task_id, payload, ip_address=request.remote_addr)
    return success_response(data=_dump(task))


@bp.post("/<int:task_id>/refer")
@require_authenticated
def refer_task(task_id: int):
    payload = TaskRefer.model_validate(request.get_json(silent=True) or {})
    assignment = services.refer_task(g.current_user, task_id, payload, ip_address=request.remote_addr)
    return success_response(
        data=TaskAssignmentPublic.model_validate(assignment).model_dump(mode="json"), status_code=201
    )


@bp.get("/<int:task_id>/assignments")
@require_authenticated
def list_assignments(task_id: int):
    return success_response(data=services.list_assignments(g.current_user, task_id))


@bp.delete("/<int:task_id>/assign/<int:assignee_user_id>")
@require_authenticated
def unassign_task(task_id: int, assignee_user_id: int):
    services.unassign_task(g.current_user, task_id, assignee_user_id, ip_address=request.remote_addr)
    return success_response(data={})


# ---- department worklist pictures (logo / header) -- admin writes, unit members read ----
@bp.get("/departments/<int:department_id>/branding/<kind>")
@require_authenticated
def get_department_picture(department_id: int, kind: str):
    path, mimetype = branding.get_picture_for_view(g.current_user, department_id, kind)
    response = send_file(path, mimetype=mimetype, as_attachment=False, max_age=0)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-cache"  # revalidated; the UI also keys by version
    return response


@bp.put("/departments/<int:department_id>/branding/<kind>")
@require_authenticated
def set_department_picture(department_id: int, kind: str):
    data = branding.set_picture(
        g.current_user, department_id, kind, request.files.get("file"), ip_address=request.remote_addr
    )
    return success_response(data=data)


@bp.delete("/departments/<int:department_id>/branding/<kind>")
@require_authenticated
def delete_department_picture(department_id: int, kind: str):
    data = branding.remove_picture(g.current_user, department_id, kind, ip_address=request.remote_addr)
    return success_response(data=data)


# ---- attachments (any number) -----------------------------------------
@bp.get("/<int:task_id>/files")
@require_authenticated
def list_files(task_id: int):
    return success_response(data=services.list_files(g.current_user, task_id))


@bp.post("/<int:task_id>/files")
@require_authenticated
def upload_files(task_id: int):
    uploads = [f for f in request.files.getlist("files") if f and f.filename] or \
        [f for f in request.files.getlist("file") if f and f.filename]
    data = services.upload_files(g.current_user, task_id, uploads, ip_address=request.remote_addr)
    return success_response(data=data, status_code=201)


@bp.get("/<int:task_id>/files/<file_id>")
@require_authenticated
def download_file(task_id: int, file_id: str):
    row, path = services.get_file_for_download(g.current_user, task_id, file_id)
    response = send_file(
        path, as_attachment=True, download_name=row.original_name,
        mimetype=row.content_type or "application/octet-stream",
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.delete("/<int:task_id>/files/<file_id>")
@require_authenticated
def delete_file(task_id: int, file_id: str):
    services.delete_file(g.current_user, task_id, file_id, ip_address=request.remote_addr)
    return success_response(data={})


# ---- internal notes -------------------------------------------------
@bp.get("/<int:task_id>/mention-candidates")
@require_authenticated
def mention_candidates(task_id: int):
    return success_response(data=services.mention_candidates(g.current_user, task_id))


@bp.get("/<int:task_id>/notes")
@require_authenticated
def list_notes(task_id: int):
    return success_response(data=services.list_notes(g.current_user, task_id))


@bp.post("/<int:task_id>/notes")
@require_authenticated
def add_note(task_id: int):
    payload = NoteCreate.model_validate(request.get_json(silent=True) or {})
    data = services.add_note(g.current_user, task_id, payload, ip_address=request.remote_addr)
    return success_response(data=data, status_code=201)


@bp.delete("/<int:task_id>/notes/<int:note_id>")
@require_authenticated
def delete_note(task_id: int, note_id: int):
    services.delete_note(g.current_user, task_id, note_id, ip_address=request.remote_addr)
    return success_response(data={})


# ---- checklist ------------------------------------------------------
@bp.get("/<int:task_id>/checklist")
@require_authenticated
def list_checklist(task_id: int):
    return success_response(data=services.list_checklist(g.current_user, task_id))


@bp.post("/<int:task_id>/checklist")
@require_authenticated
def add_checklist_item(task_id: int):
    payload = ChecklistCreate.model_validate(request.get_json(silent=True) or {})
    data = services.add_checklist_item(g.current_user, task_id, payload, ip_address=request.remote_addr)
    return success_response(data=data, status_code=201)


@bp.patch("/<int:task_id>/checklist/<int:item_id>")
@require_authenticated
def update_checklist_item(task_id: int, item_id: int):
    payload = ChecklistUpdate.model_validate(request.get_json(silent=True) or {})
    data = services.update_checklist_item(
        g.current_user, task_id, item_id, payload, ip_address=request.remote_addr
    )
    return success_response(data=data)


@bp.delete("/<int:task_id>/checklist/<int:item_id>")
@require_authenticated
def delete_checklist_item(task_id: int, item_id: int):
    services.delete_checklist_item(g.current_user, task_id, item_id, ip_address=request.remote_addr)
    return success_response(data={})
