from typing import Literal, Optional

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: Literal["shopping", "message", "task", "routine", "checklist"]
    content: dict = Field(default_factory=dict)
    description: str = Field("", max_length=1000)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[dict] = None
    description: Optional[str] = Field(None, max_length=1000)


class TemplateOut(BaseModel):
    id: str
    name: str
    category: str
    content: dict
    description: str = ""
    use_count: int = 0
    last_used: Optional[str] = None
    created_at: str
