"""
Pydantic schemas for the auth endpoints -- SECURITY.md §4: "every request
body validated through a Pydantic schema before it reaches a service."
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """POST /api/auth/login body. `identifier` accepts either a username
    or an email -- app/core/auth/services.py::_find_user_by_identifier
    checks both."""

    identifier: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    """POST /api/auth/change-password -- a user changes THEIR OWN password."""

    current_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=8, max_length=255)


class AvatarUpload(BaseModel):
    """PUT /api/me/avatar -- `image` is a data URL (png / jpeg / webp), already downsized by the client."""

    image: str = Field(..., min_length=30, max_length=420_000)


class RoleRef(BaseModel):
    name: str
    display_name: str | None = None


class UserPublic(BaseModel):
    """
    The ONLY user fields ever returned by GET /api/me or embedded in a
    login response -- per the approved decisions, this excludes
    `password_hash` and anything token-related by construction (they
    simply aren't listed here).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    username: str
    organization_id: int | None
    department_id: int | None
    is_active: bool
    last_login_at: datetime | None
    # The roles the user holds. The frontend derives `isAdmin` from this list (it gates the admin-only
    # "change password" button in the user-management panel); the backend still enforces admin-only
    # on POST /api/core/users/<id>/password itself.
    roles: list[RoleRef] = Field(default_factory=list)
