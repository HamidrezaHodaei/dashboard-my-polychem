"""
Response schemas for the RBAC-derived `/api/me/*` endpoints
(`/api/me/permissions`, `/api/me/navigation`).

Kept in app/permissions/ (not app/core/auth/schemas.py) because these
describe RBAC resolution output -- ARCHITECTURE.md's "module-agnostic"
RBAC engine -- not authentication itself. app/core/auth/schemas.py
stays scoped to login/token/UserPublic shapes only.
"""
from pydantic import BaseModel


class EffectivePermissionScope(BaseModel):
    """One grant covering a permission -- mirrors app/permissions/service.py's
    `Grant` dataclass exactly (scope_type/scope_id/source), so nothing
    about how a grant was resolved is lost or re-derived here."""

    scope_type: str
    scope_id: int | None
    source: str  # "role" or "user" -- includes delegated grants, which
    #               are user_permission_scopes rows like any other
    #               (DATABASE.md: delegations write into that same
    #               table), so they surface here with source="user"
    #               with no special-casing needed.


class EffectivePermission(BaseModel):
    """One permission key the user effectively holds, with every scope
    it's granted at (from any source)."""

    key: str
    scopes: list[EffectivePermissionScope]


class NavigationItem(BaseModel):
    """One menu entry the user is permitted to see. `permission` is the
    permission key that gated its inclusion (step 1 of AUTHORIZATION.md
    §5 only -- "holds this permission at all, any scope"; navigation
    visibility is not resource-specific, unlike an actual action)."""

    key: str
    label: str
    path: str
    permission: str
