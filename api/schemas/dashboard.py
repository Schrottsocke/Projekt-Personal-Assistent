"""Pydantic-Schemas fuer Dashboard-Endpunkte."""

from typing import Any

from pydantic import BaseModel


class ShoppingPreview(BaseModel):
    total: int = 0
    checked: int = 0
    pending: int = 0
    items: list[dict[str, Any]] = []


class DashboardTodayResponse(BaseModel):
    user_key: str
    calendar_connected: bool = False
    events_today: list[dict[str, Any]] = []
    shifts_today: list[dict[str, Any]] = []
    open_tasks: list[dict[str, Any]] = []
    task_count: int = 0
    shopping_preview: ShoppingPreview = ShoppingPreview()
    reminders_today: list[dict[str, Any]] = []
    unread_emails: int = 0
    email_connected: bool = False
    notifications_unread: int = 0
    notifications_latest: list[dict[str, Any]] = []


class BriefingItem(BaseModel):
    text: str = ""
    detail: str = ""


class BriefingSection(BaseModel):
    title: str
    icon: str
    items: list[BriefingItem] = []


class BriefingResponse(BaseModel):
    sections: list[BriefingSection] = []
    generated_at: str = ""


class WeeklyReviewResponse(BaseModel):
    completed_tasks: int = 0
    events_attended: int = 0
    items_shopped: int = 0
    highlights: list[str] = []
