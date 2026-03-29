from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"  # high|medium|low
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
