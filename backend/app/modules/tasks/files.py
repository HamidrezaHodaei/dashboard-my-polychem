"""
Task attachments -- any number of files per task.

Same rules as the supplier uploads: bytes on local disk under UPLOAD_DIR with a
random on-disk name, the user's file name (Persian letters included) kept only
in the DB row for display, short allow-list of document/image types, served
back only as attachments with `X-Content-Type-Options: nosniff`.
"""
import os
import re
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.extensions import db
from app.modules.tasks.models import TaskFile
from app.utils.exceptions import NotFoundError

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".txt",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip", ".rar", ".7z",
}


def _clean_name(raw: str) -> str:
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255]


def _upload_dir() -> str:
    path = os.path.join(current_app.config["UPLOAD_DIR"], "tasks")
    os.makedirs(path, exist_ok=True)
    return path


def save_task_file(task_id: int, file: FileStorage | None, *, uploaded_by_user_id: int) -> TaskFile:
    """Validates and stores ONE file; the caller commits."""
    if file is None or not file.filename:
        raise BadRequest("No file was sent. Use the form field named 'files'.")
    name = _clean_name(file.filename)
    ext = os.path.splitext(name)[1].lower()
    if not name or ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(e.lstrip(".") for e in ALLOWED_EXTENSIONS))
        raise BadRequest(f"This file type is not allowed. Allowed types: {allowed}.")
    limit = int(current_app.config.get("MAX_UPLOAD_MB", 10)) * 1024 * 1024
    data = file.stream.read(limit + 1)
    if len(data) > limit:
        raise RequestEntityTooLarge(f"File is too large (max {limit // (1024 * 1024)} MB).")
    if not data:
        raise BadRequest("The file is empty.")

    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"
    with open(os.path.join(_upload_dir(), stored_name), "wb") as fh:
        fh.write(data)
    row = TaskFile(
        id=file_id, task_id=task_id, original_name=name, stored_name=stored_name,
        content_type=(file.mimetype or None), size=len(data), uploaded_by_user_id=uploaded_by_user_id,
    )
    db.session.add(row)
    return row


def disk_path(row: TaskFile) -> str:
    path = os.path.join(_upload_dir(), row.stored_name)
    if not os.path.isfile(path):
        raise NotFoundError("The file is no longer available on the server.")
    return path


def remove_from_disk(row: TaskFile) -> None:
    try:
        os.remove(os.path.join(_upload_dir(), row.stored_name))
    except OSError:
        pass  # already gone; the DB row is what matters
