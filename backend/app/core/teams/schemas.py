"""Pydantic schemas for /api/core/teams -- SECURITY.md §4."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    department_id: int
    manager_user_id: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    manager_user_id: int | None = None
    is_active: bool | None = None


class TeamPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    department_id: int
    manager_user_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeamMemberAdd(BaseModel):
    user_id: int


class TeamMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    user_id: int
    joined_at: datetime
