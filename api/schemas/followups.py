from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FollowUpCreate(BaseModel):
    type: Literal["email", "commitment", "task"]
    title: str = Field(..., min_length=1, max_length=300)
    reference: Optional[str] = None
    due_date: Optional[str] = None
    contact_id: Optional[str] = None
    notes: Optional[str] = None


class FollowUpUpdate(BaseModel):
    status: Optional[Literal["open", "done", "cancelled"]] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None


class FollowUpOut(BaseModel):
    id: str
    type: str
    title: str
    reference: Optional[str] = None
    due_date: Optional[str] = None
    contact_id: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
