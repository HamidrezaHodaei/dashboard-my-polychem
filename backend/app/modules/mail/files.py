"""
Attachments of correspondence. Same discipline as the other modules' uploads (random on-disk name, the
original name kept only for display, served as an attachment with `nosniff`) plus what a mail attachment
needs on top:

* an allow-list of extensions -- no executables, scripts, HTML or SVG;
* the file CONTENT must match its extension (PDF / images / Office / zip signatures, plain text must be
  text), so a renamed program cannot slip through;
* per-file size (MAIL_MAX_ATTACHMENT_MB, default MAX_UPLOAD_MB), a cap on files per message and on the
  total size of one message.

Files live in UPLOAD_DIR/mail/ . A file uploaded but never attached is an "orphan" only its uploader can
see or delete.
"""
import os
import re
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from app.extensions import db
from app.modules.mail.models import MailAttachment
from app.utils.exceptions import InvalidInputError, NotFoundError

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods",
    ".csv", ".txt", ".zip",
}
MAX_FILES_PER_MESSAGE = 10
MAX_TOTAL_MB_PER_MESSAGE = 25

_ZIP = (b"PK\x03\x04", b"PK\x05\x06")
_OLE = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)
_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".docx": _ZIP, ".xlsx": _ZIP, ".pptx": _ZIP, ".odt": _ZIP, ".ods": _ZIP, ".zip": _ZIP,
    ".doc": _OLE, ".xls": _OLE, ".ppt": _OLE,
}


def _clean_name(raw: str) -> str:
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[\x00-\x1f\x7f]", "", name).strip()[:255]


def _dir() -> str:
    path = os.path.join(current_app.config["UPLOAD_DIR"], "mail")
    os.makedirs(path, exist_ok=True)
    return path


def max_file_bytes() -> int:
    mb = int(current_app.config.get("MAIL_MAX_ATTACHMENT_MB") or current_app.config.get("MAX_UPLOAD_MB", 10))
    return mb * 1024 * 1024


def _content_matches(ext: str, data: bytes) -> bool:
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext in _SIGNATURES:
        return data.startswith(_SIGNATURES[ext])
    if ext in (".txt", ".csv"):
        if b"\x00" in data:
            return False
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                data.decode("cp1256")  # Windows Arabic/Persian text files
            except UnicodeDecodeError:
                return False
        return True
    return False


def save_upload(file: FileStorage | None, *, uploaded_by_user_id: int) -> MailAttachment:
    if file is None or not file.filename:
        raise BadRequest("No file was sent. Use the form field named 'file'.")
    name = _clean_name(file.filename)
    ext = os.path.splitext(name)[1].lower()
    if not name or ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(e.lstrip(".") for e in ALLOWED_EXTENSIONS))
        raise InvalidInputError(f"This file type is not allowed. Allowed types: {allowed}.", "file")
    limit = max_file_bytes()
    data = file.stream.read(limit + 1)
    if len(data) > limit:
        raise RequestEntityTooLarge(f"File is too large (max {limit // (1024 * 1024)} MB).")
    if not data:
        raise InvalidInputError("The file is empty.", "file")
    if not _content_matches(ext, data):
        raise InvalidInputError("The file content does not match its type.", "file")
    file_id = str(uuid.uuid4())
    stored = f"{file_id}{ext}"
    with open(os.path.join(_dir(), stored), "wb") as fh:
        fh.write(data)
    row = MailAttachment(
        id=file_id, message_id=None, uploaded_by_user_id=uploaded_by_user_id, original_name=name,
        stored_name=stored, content_type=file.mimetype or None, size=len(data),
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_or_404(file_id: str) -> MailAttachment:
    row = db.session.get(MailAttachment, file_id)
    if row is None:
        raise NotFoundError("File was not found.")
    return row


def disk_path(row: MailAttachment) -> str:
    path = os.path.join(_dir(), row.stored_name)
    if not os.path.isfile(path):
        raise NotFoundError("The file is no longer available on the server.")
    return path


def remove_from_disk_if_unused(stored_name: str) -> None:
    """Delete the stored file when no attachment row refers to it any more (forwards share files)."""
    still_used = db.session.query(MailAttachment.id).filter(MailAttachment.stored_name == stored_name).first()
    if still_used is None:
        try:
            os.remove(os.path.join(_dir(), stored_name))
        except OSError:
            pass


def file_ref(row: MailAttachment) -> dict:
    return {"id": row.id, "name": row.original_name, "size": row.size, "content_type": row.content_type}
