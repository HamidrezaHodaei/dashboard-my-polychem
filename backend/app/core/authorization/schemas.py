"""Pydantic schemas for /api/authz/delegations -- Phase 4, wrapping
Phase 2's app/permissions/delegation.py."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DelegationCreate(BaseModel):
    delegatee_user_id: int
    permission_key: str
    scope_type: str
    scope_id: int | None = None


class DelegationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delegator_user_id: int
    delegatee_user_id: int
    resulting_user_permission_scope_id: int
    delegated_at: datetime
    revoked_at: datetime | None
    revoked_by_user_id: int | None
