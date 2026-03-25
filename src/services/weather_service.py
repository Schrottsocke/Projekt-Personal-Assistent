"""
Wetter-Service: Echtzeit-Wetterdaten via Open-Meteo (kostenlos, kein API-Key).
Geocoding via Nominatim (OpenStreetMap).
"""
import logging
from datetime import datetime
from typing import Optional

import httpx
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)

# WMO Wetter-Codes → Emoji + Beschreibung
WMO_CODES = {
      0:  ("☀️",  "Klar"),
      1:  ("🌤️", "Überwiegend klar"),
      2:  ("⛅",  "Teils bewölkt"),
      3:  ("☁️",  "Bedeckt"),
      45: ("🌫️", "Nebel"),
      48: ("🌫️", "Gefrierender Nebel"),
      51: ("🌦️", "Leichter Nieselregen"),
      53: ("🌦️", "Mäßiger Nieselregen"),
      55: ("🌧️", "Starker Nieselregen"),
      61: ("🌧️", "Leichter Regen"),
      63: ("🌧️", "Mäßiger Regen"),
      65: ("🌧️", "Starker Regen"),
      71: ("🌨️", "Leichter Schneefall"),
      73: ("🌨️", "Mäßiger Schneefall"),
      75: ("❄️",  "Starker Schneefall"),
      77: ("🌨️", "Schneegriesel"),
      80: ("🌦️", "Leichte Regenschauer"),
      81: ("🌧️", "Mäßige Regenschauer"),
      82: ("⛈️",  "Starke Regenschauer"),
      85: ("🌨️", "Schneeschauer"),
      86: ("❄️",  "Starke Schneeschauer"),
      95: ("⛈️",  "Gewitter"),
      96: ("⛈️",  "Gewitter mit leichtem Hagel"),
      99: ("⛈️",  "Gewitter mit starkem Hagel"),
}

WIND_DIRECTIONS = [
      "N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO",
      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def _wind_dir_label(degrees: float) -> str:
      """Konvertiert Windrichtung in Grad zu Himmelsrichtung."""
      idx = round(degrees / 22.5) % 16
      return WIND_DIRECTIONS[idx]


class WeatherService:
      """
          Liefert Echtzeit-Wetterdaten und stündliche/tägliche Forecasts.
              Nutzt ausschließlich kostenlose, schlüsselfreie APIs:
                    - Nominatim (OSM) für Geocoding
                          - Open-Meteo für Wetterdaten
                              """

    GEOCODING_URL = "https://nominatim.openstreetmap.org/search"
    WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
              self.tz = pytz.timezone(settings.TIMEZONE)
              self._http = httpx.AsyncClient(
                  timeout=httpx.Timeout(10.0),
                  headers={"User-Agent": "PersonalAssistantBot/1.0"},
              )

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    async def geocode(self, location: str) -> Optional[dict]:
              """
                      Gibt {'lat': float, 'lon': float, 'display_name': str} zurück
                              oder None wenn Ort nicht gefunden.
                                      """
              try:
                            resp = await self._http.get(
                                              self.GEOCODING_URL,
                                              params={
                                                                    "q": location,
                                                                    "format": "json",
                                                                    "limit": 1,
                                                                    "accept-language": "de",
                                              },
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            if not data:
                                              return None
                                          return {
                                "lat": float(data[0]["lat"]),
                                "lon": float(data[0]["lon"]),
                                "display_name": data[0].get("display_name", location),
                            }
except Exception as e:
            logger.error(f"Geocoding-Fehler für '{location}': {e}")
            return None

    # ------------------------------------------------------------------
    # Wetter abrufen
    # ------------------------------------------------------------------

    async def get_current(self, location: str) -> Optional[dict]:
              """
                      Gibt aktuelles Wetter als dict zurück:
                              {
                                          'location': str,
                                                      'temperature': float,
                                                                  'feels_like': float,
                                                                              'humidity': int,
                                                                                          'wind_speed': float,
                                                                                                      'wind_direction': str,
                                                                                                                  'weather_code': int,
                                                                                                                              'weather_emoji': str,
                                                                                                                                          'weather_desc': str,
                                                                                                                                                      'precipitation': float,
                                                                                                                                                                  'uv_index': float,
                                                                                                                                                                              'is_day': bool,
                                                                                                                                                                                      }
                                                                                                                                                                                              """
              geo = await self.geocode(location)
              if not geo:
                            return None

              try:
                            resp = await self._http.get(
                                              self.WEATHER_URL,
                                              params={
                                                                    "latitude":  geo["lat"],
                                                                    "longitude": geo["lon"],
                                                                    "current": [
                                                                                              "temperature_2m",
                                                                                              "apparent_temperature",
                                                                                              "relative_humidity_2m",
                                                                                              "precipitation",
                                                                                              "weather_code",
                                                                                              "wind_speed_10m",
                                                                                              "wind_direction_10m",
                                                                                              "uv_index",
                                                                                              "is_day",
                                                                    ],
                                                                    "wind_speed_unit": "kmh",
                                                                    "timezone": settings.TIMEZONE,
                                              },
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            cur = data.get("current", {})

                  wmo = cur.get("weather_code", 0)
            emoji, desc = WMO_CODES.get(wmo, ("🌡️", "Unbekannt"))

            return {
                              "location":      geo["display_name"],
                              "temperature":   cur.get("temperature_2m"),
                              "feels_like":    cur.get("apparent_temperature"),
                              "humidity":      cur.get("relative_humidity_2m"),
                              "wind_speed":    cur.get("wind_speed_10m"),
                              "wind_direction": _wind_dir_label(cur.get("wind_direction_10m", 0)),
                              "weather_code":  wmo,
                              "weather_emoji": emoji,
                              "weather_desc":  desc,
                              "precipitation": cur.get("precipitation", 0.0),
                              "uv_index":      cur.get("uv_index"),
                              "is_day":        bool(cur.get("is_day", 1)),
            }
except Exception as e:
            logger.error(f"Open-Meteo-Fehler: {e}")
            return None

    async def get_forecast(self, location: str, days: int = 3) -> Optional[dict]:
              """
                      Gibt Tages-Forecast für die nächsten `days` Tage zurück.
                              Jeder Tag: {'date', 'max_temp', 'min_temp', 'weather_emoji',
                                                  'weather_desc', 'precipitation_sum', 'wind_max'}
                                                          """
        geo = await self.geocode(location)
        if not geo:
                      return None

        days = min(days, 7)
        try:
                      resp = await self._http.get(
                                        self.WEATHER_URL,
                                        params={
                                                              "latitude":  geo["lat"],
                                                              "longitude": geo["lon"],
                                                              "daily": [
                                                                                        "weather_code",
                                                                                        "temperature_2m_max",
                                                                                        "temperature_2m_min",
                                                                                        "precipitation_sum",
                                                                                        "wind_speed_10m_max",
                                                                                        "uv_index_max",
                                                              ],
                                                              "forecast_days": days,
                                                              "wind_speed_unit": "kmh",
                                                              "timezone": settings.TIMEZONE,
                                        },
                      )
                      resp.raise_for_status()
                      data = resp.json()
                      daily = data.get("daily", {})

            dates      = daily.get("time", [])
            codes      = daily.get("weather_code", [])
            max_temps  = daily.get("temperature_2m_max", [])
            min_temps  = daily.get("temperature_2m_min", [])
            precip     = daily.get("precipitation_sum", [])
            wind_max   = daily.get("wind_speed_10m_max", [])
            uv_max     = daily.get("uv_index_max", [])

            forecast = []
            for i, date_str in enumerate(dates):
                              wmo = codes[i] if i < len(codes) else 0
                              emoji, desc = WMO_CODES.get(wmo, ("🌡️", "Unbekannt"))
                              forecast.append({
                                  "date":             date_str,
                                  "max_temp":         max_temps[i] if i < len(max_temps) else None,
                                  "min_temp":         min_temps[i] if i < len(min_temps) else None,
                                  "weather_emoji":    emoji,
                                  "weather_desc":     desc,
                                  "precipitation_sum": precip[i] if i < len(precip) else 0.0,
                                  "wind_max":         wind_max[i] if i < len(wind_max) else None,
                                  "uv_index_max":     uv_max[i]   if i < len(uv_max)  else None,
                              })

            return {
                              "location": geo["display_name"],
                              "days": forecast,
            }
except Exception as e:
            logger.error(f"Forecast-Fehler: {e}")
            return None

    # ------------------------------------------------------------------
    # Formatierung
    # ------------------------------------------------------------------

    def format_current(self, data: dict) -> str:
              """Formatiert aktuelles Wetter als Telegram-Markdown."""
        loc = data["location"].split(",")[0].strip()
        emoji  = data["weather_emoji"]
        desc   = data["weather_desc"]
        temp   = data["temperature"]
        feels  = data["feels_like"]
        hum    = data["humidity"]
        wind   = data["wind_speed"]
        wdir   = data["wind_direction"]
        precip = data["precipitation"]
        uv     = data["uv_index"]

        lines = [
                      f"{emoji} *Wetter in {loc}*",
                      f"",
                      f"🌡️ *Temperatur:* {temp:.1f} °C (gefühlt {feels:.1f} °C)",
                      f"🌤️ *Bedingungen:* {desc}",
                      f"💧 *Luftfeuchtigkeit:* {hum} %",
                      f"💨 *Wind:* {wind:.0f} km/h {wdir}",
        ]
        if precip and precip > 0:
                      lines.append(f"🌧️ *Niederschlag:* {precip:.1f} mm")
                  if uv is not None:
                                lines.append(f"☀️ *UV-Index:* {uv:.0f}")

        lines.append(f"\n_Daten: Open-Meteo · {datetime.now(self.tz).strftime('%H:%M Uhr')}_")
        return "\n".join(lines)

    def format_forecast(self, data: dict) -> str:
              """Formatiert Tages-Forecast als Telegram-Markdown."""
        loc = data["location"].split(",")[0].strip()
        lines = [f"📅 *Wettervorhersage für {loc}*\n"]

        for day in data["days"]:
                      date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
                      day_name = date_obj.strftime("%A, %d.%m.")

            # Deutsche Wochentage
                      de_days = {
                                        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
                                        "Thursday": "Donnerstag", "Friday": "Freitag",
                                        "Saturday": "Samstag", "Sunday": "Sonntag",
                      }
            for en, de in de_days.items():
                              day_name = day_name.replace(en, de)

            emoji = day["weather_emoji"]
            desc  = day["weather_desc"]
            hi    = day["max_temp"]
            lo    = day["min_temp"]
            rain  = day["precipitation_sum"]
            wind  = day["wind_max"]

            line = f"{emoji} *{day_name}*: {desc}, {lo:.0f}–{hi:.0f} °C"
            if rain and rain > 0.1:
                              line += f", 🌧️ {rain:.1f} mm"
                          if wind:
                                            line += f", 💨 {wind:.0f} km/h"
                                        lines.append(line)

        lines.append(f"\n_Daten: Open-Meteo_")
        return "\n".join(lines)

    async def close(self):
              """Schließt den HTTP-Client."""
        await self._http.aclose()
