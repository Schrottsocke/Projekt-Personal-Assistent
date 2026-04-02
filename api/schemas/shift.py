"""Pydantic Schemas fuer Dienstplan (ShiftType + ShiftEntry)."""

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


class ShiftEntryOut(BaseModel):
    id: int
    user_key: str
    shift_type_id: int
    date: str
    note: Optional[str]
    created_at: datetime
    # Denormalisierte Shift-Type-Infos
    shift_type_name: Optional[str] = None
    shift_type_short_name: Optional[str] = None
    shift_type_color: Optional[str] = None
    shift_type_start_time: Optional[str] = None
    shift_type_end_time: Optional[str] = None
    shift_type_category: Optional[str] = None

    class Config:
        from_attributes = True
