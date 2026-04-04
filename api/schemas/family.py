"""Pydantic-Schemas fuer Family-Produktlinie."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceOut(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceMemberAdd(BaseModel):
    user_key: str = Field(..., min_length=1)
    role: Literal["admin", "editor", "viewer"] = "viewer"


class WorkspaceMemberOut(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    invited_at: datetime
    accepted_at: Optional[datetime]

    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    role: Literal["admin", "editor", "viewer"]


class RoutineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    interval: Literal["daily", "weekly", "monthly"] = "weekly"
    assignee_strategy: Literal["fixed", "rotation"] = "fixed"
    current_assignee_id: Optional[int] = None


class RoutineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    interval: Optional[Literal["daily", "weekly", "monthly"]] = None
    assignee_strategy: Optional[Literal["fixed", "rotation"]] = None
    current_assignee_id: Optional[int] = None


class RoutineOut(BaseModel):
    id: int
    workspace_id: int
    name: str
    interval: str
    assignee_strategy: str
    current_assignee_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class RoutineCompletionCreate(BaseModel):
    photo_url: Optional[str] = Field(None, max_length=500)


class RoutineCompletionOut(BaseModel):
    id: int
    routine_id: int
    completed_by: int
    completed_at: datetime
    photo_url: Optional[str]

    class Config:
        from_attributes = True


class WorkspaceDetail(BaseModel):
    workspace: WorkspaceOut
    members: list[WorkspaceMemberOut]
    routine_count: int
