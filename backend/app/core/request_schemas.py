"""Request bodies shared by the suppliers and customers review workflow."""
from pydantic import BaseModel, Field, field_validator


class ReviewIn(BaseModel):
    """POST /api/suppliers/<id>/review (and the same shape for customers)."""

    action: str = Field(..., pattern="^(APPROVE|REJECT|REQUEST_EDIT|REOPEN)$")
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note", mode="before")
    @classmethod
    def _note(cls, v):
        if v is None:
            return None
        out = " ".join(str(v).split())
        return out or None


class ChangeRequestIn(BaseModel):
    """The creator of a finalised request asks the manager to allow a change."""

    reason: str = Field(..., min_length=3, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, v):
        out = " ".join(str(v or "").split())
        if len(out) < 3:
            raise ValueError("Explain why the information must be changed.")
        return out
