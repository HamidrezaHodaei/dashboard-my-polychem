"""Attachments of request samples (technical documents, test results, dispatch documents, feedback files).

Same rules as the other modules' uploads: random on-disk name, original name kept for display,
served only as an attachment with `nosniff`, short allow-list of types, size limit MAX_UPLOAD_MB.
"""
import os
import re
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.extensions import db
from app.modules.request_samples.models import RequestSampleFile
from app.utils.exceptions import NotFoundError

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
KINDS = ("TECHNICAL", "DISPATCH", "FOLLOWUP", "FEEDBACK", "OTHER")


def _clean_name(raw: str) -> str:
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[\x00-\x1f\x7f]", "", name).strip()[:255]


def _upload_dir() -> str:
    path = current_app.config["UPLOAD_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(file: FileStorage | None, *, uploaded_by_user_id: int, kind: str = "OTHER",
                request_id: int | None = None) -> RequestSampleFile:
    if file is None or not file.filename:
        raise BadRequest("No file was sent. Use the form field named 'file'.")
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
    stored = f"{file_id}{ext}"
    with open(os.path.join(_upload_dir(), stored), "wb") as fh:
        fh.write(data)
    row = RequestSampleFile(
        id=file_id, request_id=request_id, kind=kind if kind in KINDS else "OTHER", original_name=name,
        stored_name=stored, content_type=file.mimetype or None, size=len(data),
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_file_or_404(file_id: str) -> RequestSampleFile:
    row = db.session.get(RequestSampleFile, file_id)
    if row is None:
        raise NotFoundError("File was not found.")
    return row


def disk_path(row: RequestSampleFile) -> str:
    path = os.path.join(_upload_dir(), row.stored_name)
    if not os.path.isfile(path):
        raise NotFoundError("The file is no longer available on the server.")
    return path


def file_ref(row: RequestSampleFile) -> dict:
    return {"id": row.id, "name": row.original_name, "size": row.size, "kind": row.kind,
            "uploaded_at": row.created_at.isoformat() if row.created_at else None}
