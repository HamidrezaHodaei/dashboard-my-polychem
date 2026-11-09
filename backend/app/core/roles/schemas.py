"""Pydantic schemas for /api/core/roles -- SECURITY.md §4."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    # is_system_role is deliberately NOT accepted here -- system roles
    # are seeded (scripts/seed_roles_permissions.py), never created
    # through ordinary admin CRUD (Role model docstring).


class RoleUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    # `name` and `is_system_role` are immutable via this endpoint once
    # created -- `name` is the machine-readable key other rows/config may
    # already reference by convention, and `is_system_role` must never be
    # toggled off through ordinary CRUD (Role model docstring).


class RolePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    description: str | None
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RolePermissionGrantCreate(BaseModel):
    permission_id: int
    scope_type: str
    scope_id: int | None = None


class RolePermissionGrantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_id: int
    permission_id: int
    scope_type: str
    scope_id: int | None
    is_active: bool
    granted_by_user_id: int | None
    created_at: datetime


class RolePermissionMatrixUpdate(BaseModel):
    """{"cells": {"core.user": {"read": true, "create": false, ...}, ...}}"""

    cells: dict[str, dict[str, bool]]
