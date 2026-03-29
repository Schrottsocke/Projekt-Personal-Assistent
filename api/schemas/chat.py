from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ChatMessageIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ChatMessageOut(BaseModel):
    id: Optional[int] = None
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    response: str
    user_message: str
