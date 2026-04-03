"""POST/GET /mobility – Fahrzeit, Abfahrtszeit und Tagesfluss"""

import logging
from datetime import datetime, date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_mobility_service,
    get_calendar_service_optional,
    get_weather_service_optional,
)
from api.schemas.mobility import (
    TravelTimeRequest,
    TravelTimeResponse,
    DepartureTimeRequest,
    DepartureTimeResponse,
    DailyFlowEntry,
    DailyFlowResponse,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Profil-Mapping (natuerliche Sprache → ORS)
_PROFILE_MAP = {
    "auto": "driving-car",
    "pkw": "driving-car",
    "fahren": "driving-car",
    "fahrrad": "cycling-regular",
    "rad": "cycling-regular",
    "laufen": "foot-walking",
    "zu fuss": "foot-walking",
}

_PROFILE_ICONS = {
    "driving-car": "\U0001f697",
    "cycling-regular": "\U0001f6b2",
    "foot-walking": "\U0001f6b6",
}


def _resolve_profile(profile: str) -> str:
    """Wandelt natuerliche Sprache in ORS-Profil um."""
    return _PROFILE_MAP.get(profile.lower(), profile)


@router.post("/travel-time", response_model=TravelTimeResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def travel_time(
    request: Request,
    body: TravelTimeRequest,
    user_key: Annotated[str, Depends(get_current_user)],
    mobility_svc=Depends(get_mobility_service),
):
    """Berechnet die Fahrzeit zwischen zwei Orten."""
    ors_profile = _resolve_profile(body.profile)
    result = await mobility_svc.get_travel_time(
        origin=body.origin,
        destination=body.destination,
        mode=ors_profile,
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Fahrzeit konnte nicht berechnet werden")

    icon = _PROFILE_ICONS.get(ors_profile, "\U0001f5fa")
    duration = result["duration_minutes"]
    hours = duration // 60
    mins = duration % 60
    time_str = f"{hours}h {mins}min" if hours > 0 else f"{mins} Minuten"

    return TravelTimeResponse(
        origin=result["origin"],
        destination=result["destination"],
        duration_minutes=result["duration_minutes"],
        distance_km=result["distance_km"],
        profile=body.profile,
        summary=f"{icon} {result['origin']} \u2192 {result['destination']}: {time_str} ({result['distance_km']} km)",
    )


@router.post("/departure-time", response_model=DepartureTimeResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def departure_time(
    request: Request,
    body: DepartureTimeRequest,
    user_key: Annotated[str, Depends(get_current_user)],
    mobility_svc=Depends(get_mobility_service),
):
    """Berechnet wann man losfahren muss um puenktlich anzukommen."""
    ors_profile = _resolve_profile(body.profile)
    result = await mobility_svc.get_departure_time(
        destination=body.destination,
        arrival_time=body.arrival_time,
        mode=ors_profile,
        buffer_minutes=body.buffer_minutes,
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Abfahrtszeit konnte nicht berechnet werden")

    dep_str = result["departure_time"].strftime("%H:%M")
    arr_str = result["arrival_time"].strftime("%H:%M")

    return DepartureTimeResponse(
        destination=result["destination"],
        arrival_time=result["arrival_time"],
        recommended_departure=result["departure_time"],
        travel_minutes=result["duration_minutes"],
        buffer_minutes=result["buffer_minutes"],
        summary=f"Losfahren um {dep_str} Uhr \u2192 Ankunft {arr_str} Uhr ({result['duration_minutes']} Min. + {result['buffer_minutes']} Min. Puffer)",
    )


@router.get("/daily-flow", response_model=DailyFlowResponse)
async def daily_flow(
    user_key: Annotated[str, Depends(get_current_user)],
    mobility_svc=Depends(get_mobility_service),
    calendar_svc=Depends(get_calendar_service_optional),
    weather_svc=Depends(get_weather_service_optional),
    target_date: Optional[str] = None,
):
    """Kombinierter Tagesfluss: Termine + Wetter + Abfahrtszeiten als Timeline."""
    today = target_date or date.today().isoformat()
    entries: list[DailyFlowEntry] = []
    weather_summary: Optional[str] = None

    # 1. Wetter-Zusammenfassung
    if weather_svc:
        try:
            weather_text = await weather_svc.get_weather_simple("Schwerin")
            if weather_text:
                weather_summary = weather_text
                entries.append(
                    DailyFlowEntry(
                        time="06:00",
                        type="weather_warning",
                        title="Wetter heute",
                        detail=weather_text,
                        icon="\u2601\ufe0f",
                    )
                )
        except Exception as e:
            logger.warning("Wetter fuer Tagesfluss nicht verfuegbar: %s", e)

    # 2. Kalender-Termine
    if calendar_svc:
        try:
            events = await calendar_svc.get_todays_events(user_key)
            for event in events or []:
                start = event.get("start", "")
                summary = event.get("summary", "Termin")
                location = event.get("location", "")

                # Startzeit extrahieren
                event_time = ""
                if isinstance(start, str) and "T" in start:
                    event_time = start.split("T")[1][:5]
                elif isinstance(start, dict) and "dateTime" in start:
                    event_time = start["dateTime"].split("T")[1][:5]

                entries.append(
                    DailyFlowEntry(
                        time=event_time or "ganztaegig",
                        type="event",
                        title=summary,
                        detail=location or None,
                        icon="\U0001f4c5",
                    )
                )

                # 3. Abfahrtszeit berechnen, wenn Location vorhanden
                if location and event_time and mobility_svc.available:
                    try:
                        # Ankunftszeit aus Event-Start ableiten
                        arrival_dt = datetime.fromisoformat(
                            start if isinstance(start, str) else start.get("dateTime", "")
                        )
                        dep_result = await mobility_svc.get_departure_time(
                            destination=location,
                            arrival_time=arrival_dt,
                            buffer_minutes=10,
                        )
                        if dep_result:
                            dep_time = dep_result["departure_time"].strftime("%H:%M")
                            entries.append(
                                DailyFlowEntry(
                                    time=dep_time,
                                    type="departure",
                                    title=f"Losfahren nach {location}",
                                    detail=f"{dep_result['duration_minutes']} Min. Fahrzeit + 10 Min. Puffer",
                                    icon="\U0001f697",
                                )
                            )
                    except Exception as e:
                        logger.debug("Abfahrtszeit fuer '%s' nicht berechenbar: %s", summary, e)

        except Exception as e:
            logger.warning("Kalender fuer Tagesfluss nicht verfuegbar: %s", e)

    # Nach Zeit sortieren (ganztaegig ans Ende)
    entries.sort(key=lambda e: e.time if e.time != "ganztaegig" else "99:99")

    return DailyFlowResponse(
        date=today,
        entries=entries,
        weather_summary=weather_summary,
    )
