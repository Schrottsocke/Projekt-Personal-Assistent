"""
Mobility Service: Fahrzeiten und Routenplanung via OpenRouteService.
Kostenlos bis 2000 Requests/Tag. Kein Premium-API nötig.
Integration mit Kalender: "Wann muss ich losfahren?"
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

ORS_BASE_URL = "https://api.openrouteservice.org/v2"

# Profil-Mapping von natürlicher Sprache auf ORS-Profile
_PROFILE_MAP: dict[str, str] = {
    "auto": "driving-car",
    "pkw": "driving-car",
    "fahren": "driving-car",
    "fahrrad": "cycling-regular",
    "rad": "cycling-regular",
    "e-bike": "cycling-electric",
    "laufen": "foot-walking",
    "zu fuß": "foot-walking",
    "gehen": "foot-walking",
}

_TRANSPORT_ICONS: dict[str, str] = {
    "driving-car": "🚗",
    "cycling-regular": "🚲",
    "cycling-electric": "⚡🚲",
    "foot-walking": "🚶",
}


class MobilityService:
    """
    Fahrzeit-Berechnung und Abfahrts-Empfehlung via OpenRouteService.

    Konfiguration via .env:
    - OPENROUTE_API_KEY: API-Key (kostenlos bei openrouteservice.org)
    - HOME_ADDRESS: Standard-Startadresse (z.B. "Musterstraße 1, Berlin")

    Beispiel::

        mobility = MobilityService()
        route = await mobility.get_travel_time("Berlin Hbf", "München Hbf")
        departure = await mobility.get_departure_time("Büro", arrival_time=datetime(2026,3,25,9,0))
    """

    def __init__(self):
        self._api_key = settings.OPENROUTE_API_KEY
        self._home_address = settings.HOME_ADDRESS
        self.available = bool(self._api_key)

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------

    async def _geocode(self, address: str) -> Optional[tuple[float, float]]:
        """
        Konvertiert eine Adresse in GPS-Koordinaten via ORS Geocoding.

        Returns:
            (longitude, latitude) oder None bei Fehler.
        """
        if not self._api_key:
            return None

        url = "https://api.openrouteservice.org/geocode/search"
        params = {
            "api_key": self._api_key,
            "text": address,
            "size": 1,
            "lang": "de",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                if not features:
                    logger.warning(f"Keine Koordinaten für Adresse: {address}")
                    return None
                coords = features[0]["geometry"]["coordinates"]
                return coords[0], coords[1]  # lon, lat
        except Exception as e:
            logger.error(f"Geocoding Fehler für '{address}': {e}")
            return None

    # ------------------------------------------------------------------
    # Fahrzeit-Berechnung
    # ------------------------------------------------------------------

    async def get_travel_time(
        self,
        origin: str,
        destination: str,
        mode: str = "driving-car",
        origin_coords: Optional[tuple] = None,
        destination_coords: Optional[tuple] = None,
    ) -> Optional[dict]:
        """
        Berechnet die Fahrzeit zwischen zwei Orten.

        Args:
            origin: Startadresse (oder HOME_ADDRESS als Default)
            destination: Zieladresse
            mode: ORS-Profil (driving-car, cycling-regular, foot-walking)
            origin_coords: Optionale GPS-Koordinaten (lon, lat) statt Geocoding
            destination_coords: Optionale GPS-Koordinaten (lon, lat) statt Geocoding

        Returns:
            Dict mit: duration_minutes, distance_km, origin, destination, mode
            oder None bei Fehler.
        """
        if not self._api_key:
            return None

        # Koordinaten bestimmen
        if not origin_coords:
            start = origin or self._home_address
            if not start:
                logger.error("Kein Startpunkt und kein HOME_ADDRESS konfiguriert")
                return None
            origin_coords = await self._geocode(start)

        if not destination_coords:
            destination_coords = await self._geocode(destination)

        if not origin_coords or not destination_coords:
            logger.warning(f"Geocoding fehlgeschlagen für Route {origin} → {destination}")
            return None

        # ORS Directions API
        url = f"{ORS_BASE_URL}/directions/{mode}"
        payload = {
            "coordinates": [list(origin_coords), list(destination_coords)],
        }
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            routes = data.get("routes", [])
            if not routes:
                logger.warning(f"ORS: Keine Route gefunden für {origin} → {destination}")
                return None
            summary = routes[0]["summary"]
            duration_sec = summary.get("duration", 0)
            distance_m = summary.get("distance", 0)

            return {
                "duration_minutes": round(duration_sec / 60),
                "duration_seconds": duration_sec,
                "distance_km": round(distance_m / 1000, 1),
                "origin": origin or self._home_address,
                "destination": destination,
                "mode": mode,
            }
        except Exception as e:
            logger.error(f"ORS Directions Fehler: {e}")
            return None

    async def get_departure_time(
        self,
        destination: str,
        arrival_time: datetime,
        mode: str = "driving-car",
        buffer_minutes: int = 10,
        origin: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Berechnet wann man losfahren muss um pünktlich anzukommen.

        Args:
            destination: Zieladresse
            arrival_time: Gewünschte Ankunftszeit (timezone-aware oder naiv)
            buffer_minutes: Puffer in Minuten (Standard: 10)
            origin: Startadresse (Standard: HOME_ADDRESS)

        Returns:
            Dict mit: departure_time, duration_minutes, distance_km, arrival_time
            oder None bei Fehler.
        """
        start = origin or self._home_address
        route = await self.get_travel_time(start, destination, mode)
        if not route:
            return None

        total_minutes = route["duration_minutes"] + buffer_minutes
        departure = arrival_time - timedelta(minutes=total_minutes)

        return {
            "departure_time": departure,
            "arrival_time": arrival_time,
            "duration_minutes": route["duration_minutes"],
            "buffer_minutes": buffer_minutes,
            "distance_km": route["distance_km"],
            "origin": start,
            "destination": destination,
            "mode": mode,
        }

    # ------------------------------------------------------------------
    # Formatierung
    # ------------------------------------------------------------------

    @staticmethod
    def format_route(route_data: dict) -> str:
        """Formatiert eine Route als Telegram-Markdown."""
        mode = route_data.get("mode", "driving-car")
        icon = _TRANSPORT_ICONS.get(mode, "🗺")
        duration = route_data.get("duration_minutes", 0)
        distance = route_data.get("distance_km", 0)
        origin = route_data.get("origin", "Start")
        destination = route_data.get("destination", "Ziel")

        hours = duration // 60
        mins = duration % 60
        time_str = f"{hours}h {mins}min" if hours > 0 else f"{mins} Minuten"

        return f"{icon} *Route: {origin} → {destination}*\nFahrzeit: {time_str}\nDistanz: {distance} km"

    @staticmethod
    def format_departure(dep_data: dict) -> str:
        """Formatiert eine Abfahrts-Empfehlung als Telegram-Markdown."""
        mode = dep_data.get("mode", "driving-car")
        icon = _TRANSPORT_ICONS.get(mode, "🗺")
        departure = dep_data.get("departure_time")
        arrival = dep_data.get("arrival_time")
        duration = dep_data.get("duration_minutes", 0)
        buffer = dep_data.get("buffer_minutes", 10)
        destination = dep_data.get("destination", "Ziel")

        dep_str = departure.strftime("%H:%M") if departure else "?"
        arr_str = arrival.strftime("%H:%M") if arrival else "?"

        hours = duration // 60
        mins = duration % 60
        time_str = f"{hours}h {mins}min" if hours > 0 else f"{mins} Min."

        return (
            f"{icon} *Abfahrt für {destination}*\n"
            f"⏰ Losfahren um: *{dep_str} Uhr*\n"
            f"🎯 Ankunft: {arr_str} Uhr\n"
            f"🛣 Fahrzeit: {time_str} + {buffer} Min. Puffer"
        )
