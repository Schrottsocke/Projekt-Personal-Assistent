from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("", max_length=2000)
    priority: Literal["high", "medium", "low"] = "medium"
    due_date: Optional[datetime] = None


class TaskOut(BaseModel):
    id: int
    user_key: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    assigned_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatusUpdate(BaseModel):
    status: Literal["open", "in_progress", "done"]
