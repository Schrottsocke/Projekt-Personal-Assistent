from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CalendarEventCreate(BaseModel):
    summary: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""


class CalendarEventOut(BaseModel):
    id: Optional[str] = None
    summary: str
    start: str
    end: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    source: Optional[str] = None

    model_config = {"extra": "allow"}


class CalendarDayResponse(BaseModel):
    connected: bool
    events: list[CalendarEventOut] = []


class CalendarCreateResponse(BaseModel):
    created: bool
    event: Optional[dict] = None
