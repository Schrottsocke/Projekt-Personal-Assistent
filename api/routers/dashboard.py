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
    get_notification_service,
)
from api.schemas.dashboard import (
    BriefingResponse,
    DashboardTodayResponse,
    WeeklyReviewResponse,
)
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/today", response_model=DashboardTodayResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def dashboard_today(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    calendar_svc=Depends(get_calendar_service),
    task_svc=Depends(get_task_service),
    shopping_svc=Depends(get_shopping_service),
    reminder_svc=Depends(get_reminder_service),
    email_svc=Depends(get_email_service),
    notif_svc=Depends(get_notification_service),
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

    # Pruefen ob Services verbunden (sicher, ohne Exception)
    def _is_connected(svc, user_key):
        try:
            return svc.is_connected(user_key)
        except Exception:
            return False

    cal_connected = _is_connected(calendar_svc, user_key)
    email_connected = _is_connected(email_svc, user_key)

    # Alle Quellen parallel abrufen
    events, tasks, shopping_items, reminders, unread_count, notif_unread, notif_latest = await asyncio.gather(
        safe(calendar_svc.get_todays_events(user_key), []) if cal_connected else resolved([]),
        safe(task_svc.get_open_tasks(user_key), []),
        safe(shopping_svc.get_items(user_key, include_checked=False), []),
        safe(reminder_svc.get_todays_reminders(user_key), []),
        safe(email_svc.get_unread_count(user_key), 0) if email_connected else resolved(0),
        safe(notif_svc.count_unread(user_key), 0),
        safe(notif_svc.list(user_key, status_filter="new", limit=3), []),
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
        "calendar_connected": cal_connected,
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
        "email_connected": email_connected,
        "notifications_unread": notif_unread,
        "notifications_latest": notif_latest[:3],
    }


@router.get("/briefing", response_model=BriefingResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_briefing(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    calendar_svc=Depends(get_calendar_service),
    task_svc=Depends(get_task_service),
    shopping_svc=Depends(get_shopping_service),
    reminder_svc=Depends(get_reminder_service),
    email_svc=Depends(get_email_service),
    notif_svc=Depends(get_notification_service),
):
    """Tagesbriefing: Termine, Aufgaben, Einkauf, Erinnerungen, E-Mails, Schichten."""

    async def safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning("Briefing-Teilfehler: %s", e)
            return default

    async def resolved(value):
        return value

    sections: list[dict] = []

    # Pruefen ob Services verbunden (sicher, ohne Exception)
    def _is_connected(svc, user_key):
        try:
            return svc.is_connected(user_key)
        except Exception:
            return False

    cal_connected = _is_connected(calendar_svc, user_key)
    email_connected = _is_connected(email_svc, user_key)

    # Parallel alle Quellen abrufen
    events, tasks, shopping_items, reminders, unread_count, notif_unread = await asyncio.gather(
        safe(calendar_svc.get_todays_events(user_key), []) if cal_connected else resolved([]),
        safe(task_svc.get_open_tasks(user_key), []),
        safe(shopping_svc.get_items(user_key, include_checked=False), []),
        safe(reminder_svc.get_todays_reminders(user_key), []),
        safe(email_svc.get_unread_count(user_key), 0) if email_connected else resolved(0),
        safe(notif_svc.count_unread(user_key), 0),
    )

    # Schichten
    from api.routers.shifts import get_shift_events_for_range

    today_str = _dt.now().strftime("%Y-%m-%d")
    try:
        shifts_today = get_shift_events_for_range(user_key, today_str, today_str)
    except Exception as e:
        logger.warning("Briefing Shift-Fehler: %s", e)
        shifts_today = []

    # 1. Schichten
    if shifts_today:
        sections.append(
            {
                "title": "Schichten heute",
                "icon": "work",
                "items": [
                    {
                        "text": s.get("summary", "Schicht"),
                        "detail": f"{s.get('start', '')} – {s.get('end', '')}",
                    }
                    for s in shifts_today[:5]
                ],
            }
        )

    # 2. Termine
    if events:
        sections.append(
            {
                "title": "Termine heute",
                "icon": "calendar_month",
                "items": [
                    {
                        "text": e.get("summary", ""),
                        "detail": e.get("start", ""),
                    }
                    for e in events[:5]
                ],
            }
        )

    # 3. Erinnerungen
    if reminders:
        sections.append(
            {
                "title": "Erinnerungen",
                "icon": "schedule",
                "items": [
                    {
                        "text": r.get("title", r.get("text", "")),
                        "detail": r.get("time", ""),
                    }
                    for r in reminders[:5]
                ],
            }
        )

    # 4. Aufgaben (faellige/ueberfaellige bevorzugt)
    if tasks:
        today = _dt.now().strftime("%Y-%m-%d")
        due_today = [t for t in tasks if t.get("due_date") and t["due_date"] <= today]
        display_tasks = due_today[:5] if due_today else tasks[:5]
        sections.append(
            {
                "title": "Aufgaben",
                "icon": "check_circle",
                "items": [
                    {
                        "text": t.get("title", ""),
                        "detail": f"Priorität: {t.get('priority', 'normal')}",
                    }
                    for t in display_tasks
                ],
            }
        )

    # 5. Einkauf
    if shopping_items:
        sections.append(
            {
                "title": "Einkaufsliste",
                "icon": "shopping_cart",
                "items": [{"text": i.get("name", ""), "detail": ""} for i in shopping_items[:5]],
            }
        )

    # 6. E-Mails
    if unread_count:
        sections.append(
            {
                "title": "E-Mails",
                "icon": "mail",
                "items": [
                    {
                        "text": f"{unread_count} ungelesene E-Mail{'s' if unread_count > 1 else ''}",
                        "detail": "",
                    }
                ],
            }
        )

    # 7. Benachrichtigungen
    if notif_unread:
        sections.append(
            {
                "title": "Benachrichtigungen",
                "icon": "notifications",
                "items": [
                    {
                        "text": f"{notif_unread} ungelesen",
                        "detail": "",
                    }
                ],
            }
        )

    return {"sections": sections, "generated_at": _dt.utcnow().isoformat()}


@router.get("/weekly-review", response_model=WeeklyReviewResponse)
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
