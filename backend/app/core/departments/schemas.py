"""Pydantic schemas for /api/core/departments -- SECURITY.md §4."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    organization_id: int
    parent_department_id: int | None = None
    manager_user_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    parent_department_id: int | None = None
    manager_user_id: int | None = None
    is_active: bool | None = None


class DepartmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    organization_id: int
    parent_department_id: int | None
    manager_user_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
