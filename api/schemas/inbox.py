from typing import Literal, Optional
from pydantic import BaseModel, Field


class InboxItemCreate(BaseModel):
    category: Literal["proposal", "approval", "followup", "system"]
    title: str = Field(..., min_length=1, max_length=300)
    message: str = Field("", max_length=2000)
    source: Optional[str] = None
    link: Optional[str] = None
    priority: int = Field(5, ge=1, le=10)


class InboxAction(BaseModel):
    action: Literal["approve", "dismiss", "snooze"]


class InboxItemOut(BaseModel):
    id: str
    category: str
    title: str
    message: str
    source: Optional[str] = None
    link: Optional[str] = None
    priority: int
    status: str
    created_at: str
    actioned_at: Optional[str] = None
