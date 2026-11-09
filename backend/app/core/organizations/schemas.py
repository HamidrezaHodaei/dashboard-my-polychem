"""Pydantic schemas for /api/core/organizations -- SECURITY.md §4."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    parent_organization_id: int | None = None


class OrganizationUpdate(BaseModel):
    """PATCH body -- every field optional; only fields actually present
    in the request are applied (see services.py's use of
    `model_dump(exclude_unset=True)`)."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    parent_organization_id: int | None = None
    is_active: bool | None = None


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_organization_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
