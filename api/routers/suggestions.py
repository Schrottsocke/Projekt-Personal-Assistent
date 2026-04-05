"""GET /suggestions/chat, GET /suggestions/proactive – Kontextuelle Vorschlaege"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Annotated


from fastapi import APIRouter, Depends, HTTPException, Request
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
from api.schemas.suggestions import ChatSuggestionOut, ProactiveSuggestionOut
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_slot() -> str:
    """Tageszeit-Slot: morning, midday, afternoon, evening, night."""
    h = datetime.now().hour
    if 6 <= h < 11:
        return "morning"
    if 11 <= h < 14:
        return "midday"
    if 14 <= h < 18:
        return "afternoon"
    if 18 <= h < 23:
        return "evening"
    return "night"


async def _safe(coro, default):
    try:
        return await coro
    except Exception as e:
        logger.debug("Suggestions: Service-Fehler ignoriert: %s", e)
        return default


async def _resolved(value):
    return value


# ---------------------------------------------------------------------------
# GET /suggestions/chat
# ---------------------------------------------------------------------------


@router.get("/chat", response_model=list[ChatSuggestionOut])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def chat_suggestions(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
    calendar_svc=Depends(get_calendar_service),
    shopping_svc=Depends(get_shopping_service),
    reminder_svc=Depends(get_reminder_service),
    email_svc=Depends(get_email_service),
):
    """Liefert 3-5 kontextuelle Chat-Vorschlaege basierend auf Tageszeit und Nutzerdaten."""

    try:
        # Parallele Datenabfrage
        cal_connected = calendar_svc.is_connected(user_key)
        email_connected = email_svc.is_connected(user_key)

        tasks, events, shopping_items, reminders, unread_emails = await asyncio.gather(
            _safe(task_svc.get_open_tasks(user_key), []),
            _safe(calendar_svc.get_todays_events(user_key), []) if cal_connected else _resolved([]),
            _safe(shopping_svc.get_items(user_key, include_checked=False), []),
            _safe(reminder_svc.get_todays_reminders(user_key), []),
            _safe(email_svc.get_unread_count(user_key), 0) if email_connected else _resolved(0),
        )

        slot = _time_slot()
        suggestions: list[ChatSuggestionOut] = []

        # --- Tageszeit-basierte Vorschlaege ---
        if slot == "morning":
            suggestions.append(
                ChatSuggestionOut(
                    label="Briefing",
                    message="Gib mir ein Briefing fuer heute",
                    icon="wb_sunny",
                    priority=10,
                )
            )
        elif slot == "evening":
            suggestions.append(
                ChatSuggestionOut(
                    label="Zusammenfassung",
                    message="Fasse meinen Tag zusammen",
                    icon="nightlight",
                    priority=10,
                )
            )

        # --- Aufgaben ---
        high_prio = [t for t in tasks if t.get("priority") == "high"]
        if high_prio:
            n = len(high_prio)
            suggestions.append(
                ChatSuggestionOut(
                    label=f"{n} dringende Aufgabe{'n' if n > 1 else ''}",
                    message="Zeig mir meine dringenden Aufgaben",
                    icon="priority_high",
                    priority=9,
                )
            )
        elif tasks:
            n = len(tasks)
            suggestions.append(
                ChatSuggestionOut(
                    label=f"{n} offene Aufgabe{'n' if n > 1 else ''}",
                    message="Was muss ich heute erledigen?",
                    icon="check_circle",
                    priority=5,
                )
            )

        # --- Termine ---
        if events:
            next_event = events[0]
            summary = next_event.get("summary", "Termin")
            suggestions.append(
                ChatSuggestionOut(
                    label=f"Naechster Termin: {summary[:25]}",
                    message="Was steht heute an?",
                    icon="event",
                    priority=7,
                )
            )
        elif slot in ("morning", "midday"):
            suggestions.append(
                ChatSuggestionOut(
                    label="Tagesplan",
                    message="Was steht heute an?",
                    icon="calendar_month",
                    priority=4,
                )
            )

        # --- Einkauf ---
        pending = [i for i in shopping_items if not i.get("checked")]
        if len(pending) >= 3:
            suggestions.append(
                ChatSuggestionOut(
                    label=f"{len(pending)} Sachen einkaufen",
                    message="Zeig die Einkaufsliste",
                    icon="shopping_cart",
                    priority=6 if slot == "midday" else 3,
                )
            )

        # --- E-Mails ---
        if unread_emails and unread_emails > 0:
            suggestions.append(
                ChatSuggestionOut(
                    label=f"{unread_emails} neue E-Mail{'s' if unread_emails > 1 else ''}",
                    message="Fasse meine neuen E-Mails zusammen",
                    icon="mail",
                    priority=5,
                )
            )

        # --- Essensplanung (Mittag) ---
        if slot == "midday":
            suggestions.append(
                ChatSuggestionOut(
                    label="Was koche ich?",
                    message="Schlage mir ein Rezept fuer heute Abend vor",
                    icon="restaurant",
                    priority=4,
                )
            )

        # Sortieren nach Prioritaet (hoch zuerst), max 5
        suggestions.sort(key=lambda s: s.priority, reverse=True)
        return suggestions[:5]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat-Vorschlaege fehlgeschlagen: %s", e)
        raise HTTPException(status_code=502, detail="Vorschlaege konnten nicht geladen werden")


# ---------------------------------------------------------------------------
# GET /suggestions/proactive
# ---------------------------------------------------------------------------


@router.get("/proactive", response_model=list[ProactiveSuggestionOut])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def proactive_suggestions(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
    calendar_svc=Depends(get_calendar_service),
    shopping_svc=Depends(get_shopping_service),
    email_svc=Depends(get_email_service),
):
    """Liefert proaktive Erinnerungen basierend auf aktuellem Kontext."""

    try:
        cal_connected = calendar_svc.is_connected(user_key)
        email_connected = email_svc.is_connected(user_key)

        tasks, events, shopping_items, unread_emails = await asyncio.gather(
            _safe(task_svc.get_open_tasks(user_key), []),
            _safe(calendar_svc.get_todays_events(user_key), []) if cal_connected else _resolved([]),
            _safe(shopping_svc.get_items(user_key, include_checked=False), []),
            _safe(email_svc.get_unread_count(user_key), 0) if email_connected else _resolved(0),
        )

        now = datetime.now()
        suggestions: list[ProactiveSuggestionOut] = []

        # --- Faellige Tasks ---
        due_soon = []
        for t in tasks:
            due = t.get("due_date")
            if due:
                try:
                    due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00")).replace(tzinfo=None)
                    if due_dt.date() <= (now + timedelta(days=1)).date():
                        due_soon.append(t)
                except (ValueError, TypeError):
                    pass

        if due_soon:
            n = len(due_soon)
            first_title = due_soon[0].get("title", "Aufgabe")
            body = first_title if n == 1 else f"{first_title} und {n - 1} weitere"
            suggestions.append(
                ProactiveSuggestionOut(
                    id=f"tasks-due-{now.strftime('%Y%m%d')}",
                    type="tasks",
                    title=f"{n} faellige Aufgabe{'n' if n > 1 else ''}",
                    body=body,
                    action_route="#/tasks",
                    action_label="Aufgaben ansehen",
                )
            )

        # --- Anstehende Termine (naechste 2 Stunden) ---
        upcoming = []
        for e in events:
            start_str = e.get("start", "")
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(str(start_str).replace("Z", "+00:00")).replace(tzinfo=None)
                    diff = (start_dt - now).total_seconds()
                    if 0 < diff <= 7200:  # 2 Stunden
                        upcoming.append(e)
                except (ValueError, TypeError):
                    pass

        if upcoming:
            ev = upcoming[0]
            summary = ev.get("summary", "Termin")
            start_str = ev.get("start", "")
            try:
                start_dt = datetime.fromisoformat(str(start_str).replace("Z", "+00:00")).replace(tzinfo=None)
                minutes = int((start_dt - now).total_seconds() / 60)
                time_label = f"in {minutes} Minuten" if minutes > 0 else "jetzt"
            except (ValueError, TypeError):
                time_label = "bald"
            suggestions.append(
                ProactiveSuggestionOut(
                    id=f"event-{hashlib.md5(summary.encode()).hexdigest()[:8]}",
                    type="calendar",
                    title=f"{summary}",
                    body=f"Beginnt {time_label}",
                    action_route="#/calendar",
                    action_label="Kalender oeffnen",
                )
            )

        # --- Einkaufsliste ---
        pending = [i for i in shopping_items if not i.get("checked")]
        if len(pending) >= 5:
            suggestions.append(
                ProactiveSuggestionOut(
                    id=f"shopping-{now.strftime('%Y%m%d')}",
                    type="shopping",
                    title="Einkaufsliste wartet",
                    body=f"{len(pending)} offene Artikel",
                    action_route="#/shopping",
                    action_label="Einkaufsliste oeffnen",
                )
            )

        # --- Ungelesene E-Mails ---
        if unread_emails and unread_emails >= 3:
            suggestions.append(
                ProactiveSuggestionOut(
                    id=f"emails-{now.strftime('%Y%m%d')}",
                    type="email",
                    title=f"{unread_emails} ungelesene E-Mails",
                    body="Schau mal in dein Postfach",
                    action_route="#/chat",
                    action_label="E-Mails zusammenfassen",
                )
            )

        return suggestions

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Proaktive Vorschlaege fehlgeschlagen: %s", e)
        raise HTTPException(status_code=502, detail="Vorschlaege konnten nicht geladen werden")
