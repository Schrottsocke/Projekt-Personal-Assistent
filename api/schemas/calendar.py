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
    id: Optional[str]
    summary: str
    start: str
    end: str
    description: Optional[str] = ""
    location: Optional[str] = ""
