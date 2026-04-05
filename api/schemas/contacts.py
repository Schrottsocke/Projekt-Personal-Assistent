from typing import Optional

from pydantic import ConfigDict, BaseModel, Field


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    source: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    source: Optional[str] = None


class ContactOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    last_interaction: Optional[str] = None
    source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
