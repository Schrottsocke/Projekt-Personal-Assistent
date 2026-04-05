"""Pydantic-Schemas fuer Email-Endpunkte."""

from pydantic import BaseModel, Field


class EmailHealthResponse(BaseModel):
    status: str = "ok"


class EmailSummary(BaseModel):
    id: str = ""
    subject: str = "(Kein Betreff)"
    from_: str = Field(default="Unbekannt", alias="from")
    date: str = ""
    snippet: str = ""
    is_unread: bool = False

    model_config = {"populate_by_name": True}


class EmailDetail(BaseModel):
    id: str = ""
    subject: str = "(Kein Betreff)"
    from_: str = Field(default="Unbekannt", alias="from")
    to: str = ""
    date: str = ""
    body: str = ""
    snippet: str = ""
