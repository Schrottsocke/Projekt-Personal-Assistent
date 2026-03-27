import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Wetter-Service basierend auf wttr.in (kostenlos, kein API-Key noetig).
    Liefert aktuelles Wetter und Vorhersagen fuer beliebige Orte.

    HINWEIS: Diese Implementierung ersetzt die urspruengliche Open-Meteo-Version.
    Grund: wttr.in ist einfacher, zuverlaessiger und benoetigt keine Geocoding-API.

    Kein API-Key erforderlich - wttr.in ist ein oeffentlicher Dienst.
    Dokumentation: https://wttr.in/:help
    """

    BASE_URL = "https://wttr.in"

    @property
    def available(self) -> bool:
        """WeatherService ist immer verfuegbar (kein API-Key noetig)."""
        return True

    async def get_weather(self, location: str, lang: str = "de") -> Optional[str]:
        """
        Ruft das aktuelle Wetter fuer einen Ort ab.

        Args:
            location: Ortsname (z.B. 'Schwerin', 'Berlin', 'Hamburg')
            lang: Sprache fuer die Wetterbeschreibung (Standard: 'de')

        Returns:
            Formatierte Wetternachricht oder None bei Fehler
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.BASE_URL}/{location}"
                params = {
                    "format": "j1",  # JSON Format
                    "lang": lang
                }
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    logger.warning(f"wttr.in Fehler: {response.status_code} fuer {location}")
                    return None

                data = response.json()
                current = data["current_condition"][0]
                weather = data["weather"][0]

                temp_c = current["temp_C"]
                feels_like = current["FeelsLikeC"]
                humidity = current["humidity"]
                wind_kmph = current["windspeedKmph"]
                desc = current["lang_de"][0]["value"] if "lang_de" in current else current["weatherDesc"][0]["value"]

                # Heutige Vorhersage
                max_temp = weather["maxtempC"]
                min_temp = weather["mintempC"]

                result = (
                    f"Wetter in {location}:\n"
                    f"\U0001f321 Aktuell: {temp_c}\u00b0C (gef\u00fchlt {feels_like}\u00b0C)\n"
                    f"\U0001f4ca Heute: {min_temp}\u00b0C \u2013 {max_temp}\u00b0C\n"
                    f"\u2601 {desc}\n"
                    f"\U0001f4a7 Luftfeuchtigkeit: {humidity}%\n"
                    f"\U0001f4a8 Wind: {wind_kmph} km/h\n"
                )

                # Morgen und uebermorgen
                for i, label in enumerate(["Morgen", "\u00dcbermorgen"], start=1):
                    if i < len(data["weather"]):
                        w = data["weather"][i]
                        hourly = w.get("hourly", [])
                        desc_day = hourly[4]["lang_de"][0]["value"] if hourly and "lang_de" in hourly[4] else ""
                        result += f"\n\U0001f4c5 {label}: {w['mintempC']}\u00b0C \u2013 {w['maxtempC']}\u00b0C {desc_day}"

                return result

        except Exception as e:
            logger.error(f"WeatherService Fehler: {e}")
            return None

    async def get_weather_simple(self, location: str) -> Optional[str]:
        """
        Ruft einfaches Wetter-Format ab (Fallback falls JSON-API Probleme hat).

        Args:
            location: Ortsname

        Returns:
            Einfache Wetter-Zeile oder None bei Fehler
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.BASE_URL}/{location}"
                params = {"format": "%l:+%c+%t+(%f),+%h+Luftfeuchte,+%w+Wind"}
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.text.strip()
                return None
        except Exception as e:
            logger.error(f"WeatherService Simple Fehler: {e}")
            return None
