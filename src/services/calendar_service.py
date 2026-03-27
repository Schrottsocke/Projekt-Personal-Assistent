"""
Google Calendar Service: OAuth2-Authentifizierung und CRUD-Operationen.
Jeder User hat eigene OAuth-Credentials.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz
from google.auth.exceptions import RefreshError, TransportError

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    """
    Google Calendar Service mit per-User OAuth2.
    Tokens werden in data/google_token_{user}.json gespeichert.
    """

    def __init__(self):
        self.tz = pytz.timezone(settings.TIMEZONE)
        self._credentials: dict = {}  # user_key -> Credentials
        self._cache: dict[str, tuple[list, datetime]] = {}  # key → (data, expires_at)

    def _get_cached(self, key: str) -> list | None:
        entry = self._cache.get(key)
        if entry and datetime.utcnow() < entry[1]:
            return entry[0]
        return None

    def _set_cached(self, key: str, data: list):
        ttl = settings.CALENDAR_CACHE_TTL_MINUTES
        self._cache[key] = (data, datetime.utcnow() + timedelta(minutes=ttl))

    def _invalidate_cache(self, user_key: str):
        """Löscht alle Cache-Einträge für einen User (nach create/delete)."""
        self._cache = {k: v for k, v in self._cache.items() if user_key not in k}

    async def initialize(self):
        """Lädt bestehende Tokens beim Start und validiert Google Credentials."""
        self._credentials_available = self._validate_google_credentials()

        bot_configs = settings.get_bot_configs()
        for user_key, config in bot_configs.items():
            token_path = config.google_token_path
            if token_path.exists():
                try:
                    self._load_credentials(user_key, token_path)
                    creds = self._credentials.get(user_key)
                    if creds and creds.expired and not creds.refresh_token:
                        logger.warning(
                            f"Google Token für '{user_key}' ist abgelaufen und kann nicht erneuert werden. "
                            "Bitte Google Calendar neu verbinden."
                        )
                        del self._credentials[user_key]
                    else:
                        logger.info(f"Google Calendar Token für '{user_key}' geladen.")
                except (json.JSONDecodeError, ValueError, RefreshError, OSError) as e:
                    logger.warning(f"Token für '{user_key}' konnte nicht geladen werden: {e}")

        if not self._credentials_available:
            logger.warning(
                "Google Calendar Service eingeschränkt: google_credentials.json fehlt oder ist ungültig. "
                "Neue OAuth-Verbindungen sind nicht möglich."
            )

    def _validate_google_credentials(self) -> bool:
        """Prüft ob google_credentials.json existiert und gültiges JSON enthält."""
        creds_path = settings.GOOGLE_CREDENTIALS_PATH
        if not creds_path.exists():
            logger.warning(f"Google Credentials nicht gefunden: {creds_path}")
            return False
        try:
            with open(creds_path) as f:
                data = json.load(f)
            # Minimale Validierung: muss client_id enthalten (installed oder web)
            client_config = data.get("installed") or data.get("web")
            if not client_config or "client_id" not in client_config:
                logger.warning(f"Google Credentials ungültig: 'client_id' fehlt in {creds_path}")
                return False
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Google Credentials nicht lesbar: {e}")
            return False

    def _load_credentials(self, user_key: str, token_path: Path):
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        self._credentials[user_key] = creds

    def _get_service(self, user_key: str):
        """Erstellt einen Google Calendar API-Service für einen User."""
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        creds = self._credentials.get(user_key)
        if not creds:
            raise ValueError(f"Keine Credentials für '{user_key}'. Bitte Google Calendar verbinden.")

        # Token erneuern falls abgelaufen
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Erneuerten Token speichern
            self._save_token(user_key, creds)

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def _save_token(self, user_key: str, creds):
        """Speichert Token auf Disk."""
        token_path = settings.get_bot_configs()[user_key].google_token_path
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    async def get_auth_url(self, user_key: str) -> str:
        """Generiert OAuth2 Authentifizierungs-URL."""
        from google_auth_oauthlib.flow import Flow

        if not getattr(self, "_credentials_available", False):
            raise FileNotFoundError(
                f"Google Credentials fehlen oder sind ungültig: {settings.GOOGLE_CREDENTIALS_PATH}\n"
                "Bitte gültige google_credentials.json von Google Cloud Console in config/ ablegen."
            )

        flow = Flow.from_client_secrets_file(
            str(settings.GOOGLE_CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",  # Desktop-Flow
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        # Flow für späteren Code-Exchange speichern
        if not hasattr(self, "_pending_flows"):
            self._pending_flows = {}
        self._pending_flows[user_key] = flow

        return auth_url

    async def exchange_code(self, user_key: str, code: str) -> bool:
        """Tauscht Auth-Code gegen Access Token aus."""
        try:
            if not hasattr(self, "_pending_flows") or user_key not in self._pending_flows:
                raise ValueError("Kein ausstehender Auth-Flow. Bitte /start erneut ausführen.")

            flow = self._pending_flows[user_key]
            flow.fetch_token(code=code)

            creds = flow.credentials
            self._credentials[user_key] = creds
            self._save_token(user_key, creds)

            del self._pending_flows[user_key]
            logger.info(f"Google Calendar für '{user_key}' erfolgreich verbunden.")
            return True

        except (ValueError, RefreshError, TransportError, OSError) as e:
            logger.error(f"Token-Exchange-Fehler für '{user_key}': {e}")
            return False

    def is_connected(self, user_key: str) -> bool:
        """Prüft ob Google Calendar verbunden ist."""
        return user_key in self._credentials and self._credentials[user_key] is not None

    async def get_upcoming_events(self, user_key: str, days: int = 7, max_results: int = 15) -> list[dict]:
        """Gibt kommende Termine zurück (mit TTL-Cache)."""
        cache_key = f"upcoming_{user_key}_{days}_{max_results}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug(f"Calendar cache hit: {cache_key}")
            return cached

        try:
            service = self._get_service(user_key)
            now = datetime.now(self.tz)
            end = now + timedelta(days=days)

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=end.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            result = events_result.get("items", [])
            self._set_cached(cache_key, result)
            return result

        except ValueError:
            raise  # Nicht-verbunden Fehler weiterwerfen
        except (RefreshError, TransportError, OSError) as e:
            logger.error(f"Calendar-GetEvents-Fehler: {e}")
            raise

    async def get_todays_events(self, user_key: str) -> list[dict]:
        """Gibt nur heutige Termine zurück (mit TTL-Cache)."""
        cache_key = f"today_{user_key}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug(f"Calendar cache hit: {cache_key}")
            return cached

        try:
            service = self._get_service(user_key)
            now = datetime.now(self.tz)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    maxResults=20,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            result = events_result.get("items", [])
            self._set_cached(cache_key, result)
            return result
        except (ValueError, RefreshError, TransportError, OSError) as e:
            logger.error(f"Calendar-GetToday-Fehler: {e}")
            return []

    async def create_event(
        self,
        user_key: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
    ) -> dict:
        """Erstellt einen neuen Kalendereintrag."""
        try:
            service = self._get_service(user_key)

            event = {
                "summary": summary,
                "description": description,
                "location": location,
                "start": {
                    "dateTime": start.isoformat(),
                    "timeZone": settings.TIMEZONE,
                },
                "end": {
                    "dateTime": end.isoformat(),
                    "timeZone": settings.TIMEZONE,
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 30},
                    ],
                },
            }

            created = service.events().insert(calendarId="primary", body=event).execute()
            self._invalidate_cache(user_key)
            logger.info(f"Event erstellt für '{user_key}': {summary}")
            return created

        except (ValueError, RefreshError, TransportError, OSError) as e:
            logger.error(f"Calendar-CreateEvent-Fehler: {e}")
            raise

    async def delete_event(self, user_key: str, event_id: str) -> bool:
        """Löscht einen Kalendereintrag."""
        try:
            service = self._get_service(user_key)
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            self._invalidate_cache(user_key)
            return True
        except (ValueError, RefreshError, TransportError, OSError) as e:
            logger.error(f"Calendar-DeleteEvent-Fehler: {e}")
            return False
