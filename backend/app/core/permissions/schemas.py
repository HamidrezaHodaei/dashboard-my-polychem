"""Pydantic schemas for /api/core/permissions -- SECURITY.md §4."""
from pydantic import BaseModel, ConfigDict, Field


class PermissionCreate(BaseModel):
    # `key` must follow [module].[resource].[action] (Permission model
    # docstring / AUTHORIZATION.md header) -- validated here rather than
    # left to a DB constraint, since MySQL has no native regex-check
    # constraint and this must behave identically on SQLite in tests.
    key: str = Field(..., pattern=r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$", max_length=150)
    is_delegable: bool = False
    description: str | None = Field(default=None, max_length=500)


class PermissionUpdate(BaseModel):
    # `key`/`module`/`resource`/`action` are immutable once created --
    # changing a permission's key out from under existing
    # role_permission_scopes/user_permission_scopes rows (which key off
    # permission_id, not the string) would silently repoint every grant
    # that holds it to a different meaning.
    is_delegable: bool | None = None
    description: str | None = Field(default=None, max_length=500)


class PermissionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    module: str
    resource: str
    action: str
    is_delegable: bool
    description: str | None
