"""GET /calendar/today, GET /calendar/week, POST /calendar/events"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_calendar_service
from api.schemas.calendar import CalendarEventCreate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _to_out(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "summary": event.get("summary", ""),
        "start": event.get("start", ""),
        "end": event.get("end", ""),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
    }


@router.get("/today")
async def calendar_today(
    user_key: Annotated[str, Depends(get_current_user)],
    cal_svc=Depends(get_calendar_service),
):
    if not cal_svc.is_connected(user_key):
        return {"connected": False, "events": []}
    events = await cal_svc.get_todays_events(user_key)
    return {"connected": True, "events": [_to_out(e) for e in events]}


@router.get("/week")
async def calendar_week(
    user_key: Annotated[str, Depends(get_current_user)],
    cal_svc=Depends(get_calendar_service),
    days: int = Query(7, ge=1, le=90),
):
    if not cal_svc.is_connected(user_key):
        return {"connected": False, "events": []}
    events = await cal_svc.get_upcoming_events(user_key, days=days)
    return {"connected": True, "events": [_to_out(e) for e in events]}


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
