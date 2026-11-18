"""Request bodies of /api/mail (Pydantic v2, same style as the other modules)."""
from pydantic import BaseModel, Field, field_validator

from app.modules.mail.models import LABELS


def _unique_ids(values: list[int]) -> list[int]:
    seen: list[int] = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


class ComposeIn(BaseModel):
    """Create / update a draft, or send directly. Recipient lists are unlimited in size (To and Cc)."""

    to: list[int] = Field(default_factory=list)
    cc: list[int] = Field(default_factory=list)
    subject: str = Field(default="", max_length=300)
    body: str = Field(default="", max_length=200_000)
    # Ids of attachments: files just uploaded by the user, or files of a message they can read
    # (which is how a forward carries the original attachments over -- they are copied).
    attachment_ids: list[str] = Field(default_factory=list)
    parent_id: int | None = None  # the message being replied to

    @field_validator("to", "cc")
    @classmethod
    def _dedupe(cls, v: list[int]) -> list[int]:
        return _unique_ids(v)

    @field_validator("subject")
    @classmethod
    def _strip_subject(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("attachment_ids")
    @classmethod
    def _dedupe_files(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v:
            if x not in out:
                out.append(x)
        return out


class ReplyIn(BaseModel):
    body: str = Field(default="", max_length=200_000)
    reply_all: bool = False
    attachment_ids: list[str] = Field(default_factory=list)
    # Extra recipients on top of the automatic ones (sender / everybody for reply-all).
    to: list[int] = Field(default_factory=list)
    cc: list[int] = Field(default_factory=list)


class MoveIn(BaseModel):
    folder: str  # inbox | archive | spam | trash

    @field_validator("folder")
    @classmethod
    def _folder(cls, v: str) -> str:
        v = (v or "").lower()
        if v not in ("inbox", "archive", "spam", "trash"):
            raise ValueError("folder must be inbox, archive, spam or trash")
        return v


class FlagsIn(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_muted: bool | None = None


class LabelsIn(BaseModel):
    labels: list[str] = Field(default_factory=list, max_length=len(LABELS))

    @field_validator("labels")
    @classmethod
    def _valid(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v:
            if x not in LABELS:
                raise ValueError(f"unknown label '{x}'")
            if x not in out:
                out.append(x)
        return out


class UnitAccessIn(BaseModel):
    department_ids: list[int] = Field(default_factory=list)

    @field_validator("department_ids")
    @classmethod
    def _dedupe(cls, v: list[int]) -> list[int]:
        return _unique_ids(v)
