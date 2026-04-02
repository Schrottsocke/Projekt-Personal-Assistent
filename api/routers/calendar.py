"""GET /calendar/today, GET /calendar/week, POST /calendar/events"""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_calendar_service
from api.routers.shifts import get_shift_events_for_range
from api.schemas.calendar import CalendarEventCreate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


def _to_out(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "summary": event.get("summary", ""),
        "start": event.get("start", ""),
        "end": event.get("end", ""),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "source": "google",
    }


def _sort_key(event: dict) -> str:
    """Sortier-Key: ISO-Datetime-String aus start extrahieren."""
    start = event.get("start", "")
    if isinstance(start, dict):
        return start.get("dateTime", start.get("date", ""))
    return str(start)


@router.get("/today")
async def calendar_today(
    user_key: Annotated[str, Depends(get_current_user)],
    cal_svc=Depends(get_calendar_service),
):
    connected = cal_svc.is_connected(user_key)
    events = []
    if connected:
        cal_events = await cal_svc.get_todays_events(user_key)
        events = [_to_out(e) for e in cal_events]

    # Shift-Eintraege fuer heute mergen
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        shift_events = get_shift_events_for_range(user_key, today_str, today_str)
        events = sorted(events + shift_events, key=_sort_key)
    except Exception as e:
        logger.warning("Shift-Events fuer heute konnten nicht geladen werden: %s", e)

    return {"connected": connected, "events": events}


@router.get("/week")
async def calendar_week(
    user_key: Annotated[str, Depends(get_current_user)],
    cal_svc=Depends(get_calendar_service),
    days: int = Query(7, ge=1, le=90),
):
    connected = cal_svc.is_connected(user_key)
    events = []
    if connected:
        cal_events = await cal_svc.get_upcoming_events(user_key, days=days)
        events = [_to_out(e) for e in cal_events]

    # Shift-Eintraege fuer den Zeitraum mergen
    today = datetime.now()
    start_str = today.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        shift_events = get_shift_events_for_range(user_key, start_str, end_str)
        events = sorted(events + shift_events, key=_sort_key)
    except Exception as e:
        logger.warning("Shift-Events fuer Woche konnten nicht geladen werden: %s", e)

    return {"connected": connected, "events": events}


@router.post("/events")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_event(
    request: Request,
    body: CalendarEventCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    cal_svc=Depends(get_calendar_service),
):
    if not cal_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Google Calendar nicht verbunden.")
    result = await cal_svc.create_event(
        user_key=user_key,
        summary=body.summary,
        start=body.start,
        end=body.end,
        description=body.description,
        location=body.location,
    )
    return {"created": True, "event": result}
