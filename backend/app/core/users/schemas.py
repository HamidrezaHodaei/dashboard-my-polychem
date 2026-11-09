"""Pydantic schemas for /api/core/users -- SECURITY.md §4."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=150)
    # Plain `str`, not pydantic's EmailStr -- consistent with
    # app/core/auth/schemas.py::UserPublic.email, and avoids adding
    # `email-validator` as a new dependency not in requirements.txt.
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=255)
    organization_id: int | None = None
    department_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(
        default=None, min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    username: str | None = Field(default=None, min_length=1, max_length=100)
    organization_id: int | None = None
    department_id: int | None = None
    is_active: bool | None = None
    # Password change deliberately NOT exposed here -- SECURITY.md keeps
    # credential rotation as its own dedicated flow (Phase 3's auth
    # module), not a field on the general admin CRUD update.


class UserPasswordSet(BaseModel):
    """POST /api/core/users/<id>/password -- an ADMIN sets a new password for a user.
    (Passwords are stored as Argon2 hashes: nobody, admins included, can read a current password.)"""

    new_password: str = Field(..., min_length=8, max_length=255)


class UserPublic(BaseModel):
    """Same safe-field contract as app/core/auth/schemas.py::UserPublic --
    never includes password_hash or token data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    username: str
    organization_id: int | None
    department_id: int | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserRoleAssign(BaseModel):
    role_id: int
    organization_id: int | None = None


class UserRolePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role_id: int
    organization_id: int | None
    assigned_at: datetime


class PermissionMatrixUpdate(BaseModel):
    """{"cells": {"core.user": {"read": true, "create": false, ...}, ...}}
    -- desired FINAL access per module/action (see app/permissions/matrix.py)."""

    cells: dict[str, dict[str, bool]]
