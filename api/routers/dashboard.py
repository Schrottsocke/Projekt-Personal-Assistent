"""GET /dashboard/today – Tages-Übersicht, GET /dashboard/weekly-review – Wochenrückblick"""

import asyncio
import logging
from datetime import datetime as _dt, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_calendar_service,
    get_task_service,
    get_shopping_service,
    get_reminder_service,
    get_email_service,
)
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/today")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def dashboard_today(
    request: Request,
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
        safe(calendar_svc.get_todays_events(user_key), []) if calendar_svc.is_connected(user_key) else resolved([]),
        safe(task_svc.get_open_tasks(user_key), []),
        safe(shopping_svc.get_items(user_key, include_checked=False), []),
        safe(reminder_svc.get_todays_reminders(user_key), []),
        safe(email_svc.get_unread_count(user_key), 0) if email_svc.is_connected(user_key) else resolved(0),
    )

    # Shift-Eintraege fuer heute
    from datetime import datetime as _dt

    from api.routers.shifts import get_shift_events_for_range

    today_str = _dt.now().strftime("%Y-%m-%d")
    try:
        shifts_today = get_shift_events_for_range(user_key, today_str, today_str)
    except Exception as e:
        logger.warning("Dashboard Shift-Fehler: %s", e)
        shifts_today = []

    # Shopping-Kurzinfo
    checked = sum(1 for i in shopping_items if i.get("checked"))
    total = len(shopping_items)

    return {
        "user_key": user_key,
        "calendar_connected": calendar_svc.is_connected(user_key),
        "events_today": events[:5],
        "shifts_today": shifts_today,
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


@router.get("/weekly-review")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def weekly_review(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    calendar_svc=Depends(get_calendar_service),
    task_svc=Depends(get_task_service),
    shopping_svc=Depends(get_shopping_service),
):
    """Kompakter Wochenrückblick: erledigte Tasks, Termine, Einkäufe."""

    async def safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning("Weekly-Review Teilfehler: %s", e)
            return default

    since = _dt.now(timezone.utc) - timedelta(days=7)

    completed_tasks, shopping_items, events = await asyncio.gather(
        safe(task_svc.get_completed_tasks_since(user_key, since), []),
        safe(shopping_svc.get_items(user_key, include_checked=True), []),
        safe(
            calendar_svc.get_upcoming_events(user_key, days=0)
            if not calendar_svc.is_connected(user_key)
            else calendar_svc.get_upcoming_events(user_key, days=0),
            [],
        ),
    )

    # Count events from this week via calendar week endpoint
    week_events = 0
    try:
        if calendar_svc.is_connected(user_key):
            week_events_list = await calendar_svc.get_upcoming_events(user_key, days=7)
            week_events = len(week_events_list)
    except Exception as e:
        logger.warning("Weekly-Review Kalender-Fehler: %s", e)

    # Shopping: count checked items (approximation – items checked this week)
    items_shopped = sum(1 for i in shopping_items if i.get("checked"))

    # Build highlights from completed tasks
    highlights = []
    for t in completed_tasks[:5]:
        label = t["title"]
        if t.get("recurrence"):
            recur_labels = {"daily": "täglich", "weekly": "wöchentlich", "monthly": "monatlich"}
            label += f" ({recur_labels.get(t['recurrence'], t['recurrence'])})"
        highlights.append(label)

    return {
        "completed_tasks": len(completed_tasks),
        "events_attended": week_events,
        "items_shopped": items_shopped,
        "highlights": highlights,
    }
