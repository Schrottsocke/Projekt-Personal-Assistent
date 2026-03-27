"""GET /calendar/today, GET /calendar/week, POST /calendar/events"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user, get_calendar_service
from api.schemas.calendar import CalendarEventCreate

router = APIRouter()


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
    days: int = 7,
):
    if not cal_svc.is_connected(user_key):
        return {"connected": False, "events": []}
    events = await cal_svc.get_upcoming_events(user_key, days=days)
    return {"connected": True, "events": [_to_out(e) for e in events]}


@router.post("/events")
async def create_event(
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
