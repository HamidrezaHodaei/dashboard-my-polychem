"""
Upload / download of logistics permit scans (international permits, carnets, licences).

Bytes go to local disk under config UPLOAD_DIR with a random on-disk name;
a `logistics_files` row keeps the original name for display. Files are only
ever served back as attachments (never rendered inline) and with
`X-Content-Type-Options: nosniff`, so an uploaded HTML/SVG can't run in the
panel's origin. Only a short allow-list of document/image types is accepted.
"""
import os
import re
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.extensions import db
from app.modules.logistics.models import LogisticsFile
from app.utils.exceptions import NotFoundError

ALLOWED_EXTENSIONS = {
    ".pdf",     ".png", ".jpg", ".jpeg", ".webp",
}


def _clean_name(raw: str) -> str:
    """Keep the user's name (Persian letters included) but drop any path part
    and control characters."""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255]


def _upload_dir() -> str:
    path = current_app.config["UPLOAD_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(file: FileStorage | None, *, uploaded_by_user_id: int | None) -> LogisticsFile:
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
    stored_name = f"{file_id}{ext}"
    with open(os.path.join(_upload_dir(), stored_name), "wb") as fh:
        fh.write(data)

    row = LogisticsFile(
        id=file_id, original_name=name, stored_name=stored_name,
        content_type=(file.mimetype or None), size=len(data),
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_file_or_404(file_id: str) -> LogisticsFile:
    row = db.session.get(LogisticsFile, file_id)
    if row is None:
        raise NotFoundError("File was not found.")
    return row


def disk_path(row: LogisticsFile) -> str:
    path = os.path.join(_upload_dir(), row.stored_name)
    if not os.path.isfile(path):
        raise NotFoundError("The file is no longer available on the server.")
    return path


def file_ref(row: LogisticsFile) -> dict:
    return {"id": row.id, "name": row.original_name, "size": row.size}


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def is_image(row: LogisticsFile) -> bool:
    return os.path.splitext(row.stored_name)[1].lower() in IMAGE_EXTENSIONS
