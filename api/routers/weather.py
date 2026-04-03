"""GET /weather – Wetter-Daten (aktuell, Vorhersage, einfach)"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_weather_service
from api.schemas.weather import WeatherCurrent, WeatherForecastDay, WeatherResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

DEFAULT_LOCATION = "Schwerin"


def _parse_weather_json(data: dict, location: str) -> WeatherResponse:
    """Parst die wttr.in JSON-Antwort in ein strukturiertes WeatherResponse."""
    current_raw = data["current_condition"][0]
    weather_today = data["weather"][0]

    desc = (
        current_raw["lang_de"][0]["value"]
        if "lang_de" in current_raw
        else current_raw["weatherDesc"][0]["value"]
    )

    current = WeatherCurrent(
        location=location,
        temp_c=float(current_raw["temp_C"]),
        feels_like_c=float(current_raw["FeelsLikeC"]),
        humidity=int(current_raw["humidity"]),
        wind_kmph=float(current_raw["windspeedKmph"]),
        description=desc,
        min_temp_c=float(weather_today["mintempC"]),
        max_temp_c=float(weather_today["maxtempC"]),
    )

    forecast: list[WeatherForecastDay] = []
    for w in data.get("weather", [])[1:]:
        hourly = w.get("hourly", [])
        day_desc = ""
        if len(hourly) > 4 and "lang_de" in hourly[4]:
            day_desc = hourly[4]["lang_de"][0]["value"]
        elif len(hourly) > 4:
            day_desc = hourly[4].get("weatherDesc", [{}])[0].get("value", "")

        forecast.append(
            WeatherForecastDay(
                date=w["date"],
                min_temp_c=float(w["mintempC"]),
                max_temp_c=float(w["maxtempC"]),
                description=day_desc,
            )
        )

    return WeatherResponse(current=current, forecast=forecast)


async def _fetch_weather_json(weather_svc, location: str) -> dict:
    """Ruft die wttr.in JSON-Daten direkt ab (ohne Formatierung)."""
    import httpx

    url = f"{weather_svc.BASE_URL}/{location}"
    params = {"format": "j1", "lang": "de"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Wetterdienst nicht erreichbar ({response.status_code})")
        data = response.json()
        if not data.get("current_condition") or not data.get("weather"):
            raise HTTPException(status_code=502, detail="Unvollstaendige Wetter-Antwort")
        if not data["current_condition"] or not data["weather"]:
            raise HTTPException(status_code=502, detail="Leere Wetter-Daten")
        return data


@router.get("/current", response_model=WeatherResponse)
async def weather_current(
    user_key: Annotated[str, Depends(get_current_user)],
    weather_svc=Depends(get_weather_service),
    location: str = DEFAULT_LOCATION,
):
    """Aktuelles Wetter mit Tagesvorhersage."""
    try:
        data = await _fetch_weather_json(weather_svc, location)
        return _parse_weather_json(data, location)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Wetter-Abfrage fehlgeschlagen: {e}")


@router.get("/forecast", response_model=list[WeatherForecastDay])
async def weather_forecast(
    user_key: Annotated[str, Depends(get_current_user)],
    weather_svc=Depends(get_weather_service),
    location: str = DEFAULT_LOCATION,
    days: int = 3,
):
    """Wettervorhersage fuer die naechsten Tage."""
    try:
        data = await _fetch_weather_json(weather_svc, location)
        response = _parse_weather_json(data, location)
        return response.forecast[:days]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vorhersage-Abfrage fehlgeschlagen: {e}")


@router.get("/simple")
async def weather_simple(
    user_key: Annotated[str, Depends(get_current_user)],
    weather_svc=Depends(get_weather_service),
    location: str = DEFAULT_LOCATION,
):
    """Einfache Wetter-Zeile (Fallback-Format)."""
    result = await weather_svc.get_weather_simple(location)
    if result is None:
        raise HTTPException(status_code=502, detail="Wetter-Abfrage fehlgeschlagen")
    return {"text": result}
