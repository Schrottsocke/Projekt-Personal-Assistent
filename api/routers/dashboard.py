"""GET /dashboard/today – Tages-Übersicht"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_current_user,
    get_calendar_service,
    get_task_service,
    get_shopping_service,
    get_reminder_service,
    get_email_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/today")
async def dashboard_today(
    user_key: Annotated[str, Depends(get_current_user)],
    calendar_svc=Depends(get_calendar_service),
    task_svc=Depends(get_task_service),
    shopping_svc=Depends(get_shopping_service),
    reminder_svc=Depends(get_reminder_service),
    email_svc=Depends(get_email_service),
):
    """Kombinierte Tages-Übersicht: Termine, Tasks, Einkauf, Erinnerungen, E-Mails."""

    async def safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning("Dashboard-Teilfehler: %s", e)
            return default

    async def resolved(value):
        return value

    # Alle Quellen parallel abrufen
    events, tasks, shopping_items, reminders, unread_count = await asyncio.gather(
        safe(calendar_svc.get_todays_events(user_key), [])
        if calendar_svc.is_connected(user_key)
        else resolved([]),
        safe(task_svc.get_open_tasks(user_key), []),
        safe(shopping_svc.get_items(user_key, include_checked=False), []),
        safe(reminder_svc.get_todays_reminders(user_key), []),
        safe(email_svc.get_unread_count(user_key), 0)
        if email_svc.is_connected(user_key)
        else resolved(0),
    )

    # Shopping-Kurzinfo
    checked = sum(1 for i in shopping_items if i.get("checked"))
    total = len(shopping_items)

    return {
        "user_key": user_key,
        "calendar_connected": calendar_svc.is_connected(user_key),
        "events_today": events[:5],
        "open_tasks": tasks[:5],
        "task_count": len(tasks),
        "shopping_preview": {
            "total": total,
            "checked": checked,
            "pending": total - checked,
            "items": shopping_items[:3],
        },
        "reminders_today": reminders,
        "unread_emails": unread_count,
        "email_connected": email_svc.is_connected(user_key),
    }
