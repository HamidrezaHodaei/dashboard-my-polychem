"""
Worklist (کارتابل واحد) pictures -- ONE logo and ONE header banner per department.

Rules (shared by every user, not a per-browser preference any more):
  * only an administrator may set / replace / remove a picture;
  * everybody who can see the department's worklist (admins: all units, everybody else: their
    own unit -- the same "unit isolation" rule as `task_meta`) gets the SAME picture;
  * bytes live on local disk under UPLOAD_DIR/departments with a random name; the picture is
    served back inline with `X-Content-Type-Options: nosniff`. Only raster formats are accepted
    (no SVG -- it can carry script), and the file signature must match the extension.
"""
import os
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.core.audit_logs.services import write_audit_log
from app.core.departments.models import Department
from app.core.users.models import User
from app.extensions import db
from app.permissions.exceptions import PermissionDeniedError
from app.permissions.service import is_admin
from app.utils.exceptions import NotFoundError

MODULE = "tasks"
KINDS = ("logo", "header")
MAX_BYTES = 3 * 1024 * 1024  # 3 MB per picture
_EXT_BY_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}


def _sniff(data: bytes) -> str | None:
    """Real content type from the file signature (the client-sent type / name is not trusted)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _dir() -> str:
    path = os.path.join(current_app.config["UPLOAD_DIR"], "departments")
    os.makedirs(path, exist_ok=True)
    return path


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise NotFoundError("Unknown picture type.")


def _department_or_404(department_id: int) -> Department:
    dept = db.session.get(Department, department_id)
    if dept is None or dept.deleted_at is not None:
        raise NotFoundError("Department was not found.")
    return dept


def _require_admin(actor: User) -> None:
    if not is_admin(actor):
        raise PermissionDeniedError(
            "permission_denied", "Only an administrator can change the worklist pictures."
        )


def _remove_from_disk(stored_name: str | None) -> None:
    if not stored_name:
        return
    try:
        os.remove(os.path.join(_dir(), stored_name))
    except OSError:
        pass  # already gone; the DB row is what matters


def branding_payload(dept: Department) -> dict:
    """What `task_meta` shows for a department (no bytes -- the picture is fetched separately)."""
    return {
        "has_logo": bool(dept.logo_file),
        "has_header": bool(dept.header_file),
        "branding_version": dept.branding_version or 0,
    }


def set_picture(
    actor: User, department_id: int, kind: str, file: FileStorage | None, *, ip_address: str | None
) -> dict:
    _check_kind(kind)
    _require_admin(actor)
    dept = _department_or_404(department_id)
    if file is None or not file.filename:
        raise BadRequest("No file was sent. Use the form field named 'file'.")
    data = file.stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RequestEntityTooLarge(f"The picture is too large (max {MAX_BYTES // (1024 * 1024)} MB).")
    if not data:
        raise BadRequest("The file is empty.")
    mime = _sniff(data)
    if mime is None:
        raise BadRequest("Only PNG, JPG, WEBP or GIF pictures are allowed.")

    stored = f"{uuid.uuid4()}{_EXT_BY_MIME[mime]}"
    with open(os.path.join(_dir(), stored), "wb") as fh:
        fh.write(data)
    old = getattr(dept, f"{kind}_file")
    setattr(dept, f"{kind}_file", stored)
    setattr(dept, f"{kind}_content_type", mime)
    dept.branding_version = (dept.branding_version or 0) + 1
    write_audit_log(
        user_id=actor.id, action=f"{kind}_set", module=MODULE, entity_type="department",
        entity_id=dept.id, metadata={"kind": kind, "size": len(data)}, ip_address=ip_address,
    )
    db.session.commit()
    _remove_from_disk(old)  # only after the new row is safely committed
    return branding_payload(dept)


def remove_picture(actor: User, department_id: int, kind: str, *, ip_address: str | None) -> dict:
    _check_kind(kind)
    _require_admin(actor)
    dept = _department_or_404(department_id)
    old = getattr(dept, f"{kind}_file")
    if old:
        setattr(dept, f"{kind}_file", None)
        setattr(dept, f"{kind}_content_type", None)
        dept.branding_version = (dept.branding_version or 0) + 1
        write_audit_log(
            user_id=actor.id, action=f"{kind}_remove", module=MODULE, entity_type="department",
            entity_id=dept.id, metadata={"kind": kind}, ip_address=ip_address,
        )
        db.session.commit()
        _remove_from_disk(old)
    return branding_payload(dept)


def get_picture_for_view(actor: User, department_id: int, kind: str) -> tuple[str, str]:
    """(path on disk, content type) -- only for someone who can see this department's worklist."""
    from app.modules.tasks.services import Authority  # local: services imports this package

    _check_kind(kind)
    dept = _department_or_404(department_id)
    auth = Authority(actor)
    if not auth.sees_all and dept.id not in set(auth.own_department_ids):
        raise PermissionDeniedError("permission_denied", "This unit's worklist is not available to you.")
    stored = getattr(dept, f"{kind}_file")
    if not stored:
        raise NotFoundError("This unit has no picture.")
    path = os.path.join(_dir(), stored)
    if not os.path.isfile(path):
        raise NotFoundError("The picture is no longer available on the server.")
    return path, getattr(dept, f"{kind}_content_type") or "application/octet-stream"
