"""Pydantic Schemas fuer Dienstplan (ShiftType + ShiftEntry + Tracking)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- ShiftType ---


class ShiftTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    short_name: str = Field(..., min_length=1, max_length=10)
    color: str = Field("#7c4dff", max_length=7)
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    break_minutes: int = Field(0, ge=0)
    category: Literal["work", "free", "vacation", "special"] = "work"
    default_note: Optional[str] = Field(None, max_length=200)
    is_active: bool = True


class ShiftTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    short_name: Optional[str] = Field(None, min_length=1, max_length=10)
    color: Optional[str] = Field(None, max_length=7)
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    break_minutes: Optional[int] = Field(None, ge=0)
    category: Optional[Literal["work", "free", "vacation", "special"]] = None
    default_note: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class ShiftTypeOut(BaseModel):
    id: int
    user_key: str
    name: str
    short_name: str
    color: str
    start_time: Optional[str]
    end_time: Optional[str]
    break_minutes: int
    category: str
    default_note: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- ShiftEntry ---


class ShiftEntryCreate(BaseModel):
    shift_type_id: int
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    note: Optional[str] = Field(None, max_length=500)


class ShiftEntryUpdate(BaseModel):
    """Manuelle Bearbeitung eines Diensteintrags."""

    actual_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    actual_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    actual_break_minutes: Optional[int] = Field(None, ge=0)
    planned_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    planned_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    break_minutes: Optional[int] = Field(None, ge=0)
    confirmation_status: Optional[Literal["pending", "confirmed", "deviation", "cancelled"]] = None
    deviation_note: Optional[str] = Field(None, max_length=500)
    note: Optional[str] = Field(None, max_length=500)


class ShiftConfirmRequest(BaseModel):
    """Quick-Confirm fuer Dienstbestaetigung."""

    action: Literal["confirm", "deviation", "cancel", "snooze"]
    actual_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    actual_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    actual_break_minutes: Optional[int] = Field(None, ge=0)
    deviation_note: Optional[str] = Field(None, max_length=500)
    snooze_minutes: int = Field(60, ge=5, le=480)


class ShiftEntryOut(BaseModel):
    id: int
    user_key: str
    shift_type_id: int
    date: str
    note: Optional[str]
    created_at: datetime

    # Soll-Zeiten (Override)
    planned_start: Optional[str] = None
    planned_end: Optional[str] = None
    break_minutes: Optional[int] = None

    # Ist-Zeiten
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    actual_break_minutes: Optional[int] = None

    # Berechnete Dauern
    planned_duration_minutes: Optional[int] = None
    actual_duration_minutes: Optional[int] = None
    delta_minutes: Optional[int] = None

    # Bestaetigungsstatus
    confirmation_status: Optional[str] = "pending"
    confirmation_source: Optional[str] = None
    confirmation_timestamp: Optional[datetime] = None
    deviation_note: Optional[str] = None

    # Reminder
    reminder_sent: Optional[bool] = False
    reminder_count: Optional[int] = 0

    # Denormalisierte Shift-Type-Infos
    shift_type_name: Optional[str] = None
    shift_type_short_name: Optional[str] = None
    shift_type_color: Optional[str] = None
    shift_type_start_time: Optional[str] = None
    shift_type_end_time: Optional[str] = None
    shift_type_category: Optional[str] = None

    class Config:
        from_attributes = True


# --- Report ---


class ShiftReportEntry(BaseModel):
    id: int
    date: str
    shift_type: str
    shift_type_short: str
    shift_color: str
    planned_start: Optional[str]
    planned_end: Optional[str]
    actual_start: Optional[str]
    actual_end: Optional[str]
    planned_duration: Optional[int]
    actual_duration: Optional[int]
    delta_minutes: Optional[int]
    status: str
    note: str
    confirmation_source: Optional[str]


class ShiftReportSummary(BaseModel):
    planned_hours: float
    actual_hours: float
    delta_hours: float
    confirmed_count: int
    pending_count: int
    deviation_count: int
    cancelled_count: int


class ShiftReportOut(BaseModel):
    month: str
    entries: list[ShiftReportEntry]
    summary: ShiftReportSummary
