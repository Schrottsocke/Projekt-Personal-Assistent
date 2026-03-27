from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    id: Optional[int] = None
    role: str          # "user" | "assistant"
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    response: str
    user_message: str
