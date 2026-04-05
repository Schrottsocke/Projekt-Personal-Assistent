from datetime import datetime
from typing import Literal, Optional
from pydantic import ConfigDict, BaseModel, Field


class NotificationCreate(BaseModel):
    type: Literal["reminder", "follow_up", "document", "inbox", "weather", "system"]
    title: str = Field(..., min_length=1, max_length=300)
    message: str = Field("", max_length=2000)
    link: Optional[str] = None


class NotificationOut(BaseModel):
    id: int
    user_key: str
    type: str
    title: str
    message: str
    status: str
    link: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class NotificationStatusUpdate(BaseModel):
    status: Literal["read", "completed", "hidden"]


class NotificationBulkUpdate(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)
    status: Literal["read", "completed", "hidden"]
