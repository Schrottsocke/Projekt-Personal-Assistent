"""
Spotify-Integration via Spotipy (Spotify Web API).
Benötigt Spotify Premium + App-Credentials.

OAuth2-Flow für Telegram:
  1. Bot sendet Auth-URL
  2. User öffnet im Browser, wird zu redirect_uri weitergeleitet
  3. User kopiert die komplette Redirect-URL und sendet sie an den Bot
  4. Bot extrahiert Code, holt Token, speichert in DB

Intents: spotify_play, spotify_pause, spotify_skip, spotify_info
"""

import asyncio
import json
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config.settings import settings

logger = logging.getLogger(__name__)

SPOTIFY_SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "playlist-read-private "
    "playlist-read-collaborative"
)


class SpotifyService:
    """
    Steuert Spotify-Wiedergabe über die Web API.
    Tokens werden pro User in der DB gespeichert.
    """

    def __init__(self):
        self._available = False
        self._sp = {}  # user_key → Spotify-Client
        self._check_availability()

    def _check_availability(self):
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            logger.info("SpotifyService: Keine Credentials konfiguriert – deaktiviert.")
            return
        try:
            import spotipy  # noqa: F401

            self._available = True
            logger.info("SpotifyService: spotipy verfügbar.")
        except ImportError:
            logger.warning("SpotifyService: spotipy nicht installiert (pip install spotipy). Deaktiviert.")

    @property
    def available(self) -> bool:
        return self._available

    def get_auth_url(self, user_key: str) -> str:
        """Erstellt die OAuth2-Auth-URL für den Nutzer."""
        from spotipy.oauth2 import SpotifyOAuth

        auth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPES,
            state=user_key,
            open_browser=False,
        )
        return auth.get_authorize_url()

    def exchange_code(self, user_key: str, redirect_url: str) -> bool:
        """
        Tauscht den Auth-Code gegen ein Token aus und speichert es in der DB.
        redirect_url: Die volle URL nach dem Redirect (inkl. ?code=...)
        Returns True bei Erfolg.
        """
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth

            # Code aus URL extrahieren
            parsed = urlparse(redirect_url)
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            if not code:
                logger.warning(f"Kein Code in URL: {redirect_url}")
                return False

            auth = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
                scope=SPOTIFY_SCOPES,
            )
            token_info = auth.get_access_token(code, as_dict=True)
            self._save_token(user_key, token_info)
            self._sp[user_key] = spotipy.Spotify(auth=token_info["access_token"])
            return True
        except Exception as e:
            logger.error(f"Spotify-Token-Exchange-Fehler: {e}")
            return False

    def is_connected(self, user_key: str) -> bool:
        """Prüft ob ein gültiger Token für den User vorliegt."""
        token = self._load_token(user_key)
        return token is not None

    def _get_client(self, user_key: str):
        """Gibt einen authentifizierten Spotify-Client zurück (mit Auto-Refresh)."""
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        token_info = self._load_token(user_key)
        if not token_info:
            return None

        auth = SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPES,
        )

        # Token ggf. erneuern
        if auth.is_token_expired(token_info):
            try:
                token_info = auth.refresh_access_token(token_info["refresh_token"])
                self._save_token(user_key, token_info)
            except Exception as e:
                logger.error(f"Spotify-Token-Refresh-Fehler: {e}")
                return None

        return spotipy.Spotify(auth=token_info["access_token"])

    # =========================================================================
    # Wiedergabe-Steuerung
    # =========================================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def play(self, user_key: str, query: str = "") -> Optional[str]:
        """
        Startet/setzt Wiedergabe fort. Wenn query angegeben, wird danach gesucht.
        Returns: Statusmeldung oder None bei Fehler.
        """
        sp = self._get_client(user_key)
        if not sp:
            return None
        loop = asyncio.get_running_loop()
        try:
            if query:
                results = await loop.run_in_executor(
                    None, lambda: sp.search(q=query, type="track,playlist,artist", limit=1)
                )
                # Track bevorzugen
                tracks = results.get("tracks", {}).get("items", [])
                playlists = results.get("playlists", {}).get("items", [])
                if tracks:
                    await loop.run_in_executor(None, lambda: sp.start_playback(uris=[tracks[0]["uri"]]))
                    return f"▶️ Spiele: *{tracks[0]['name']}* – {tracks[0]['artists'][0]['name']}"
                elif playlists:
                    await loop.run_in_executor(None, lambda: sp.start_playback(context_uri=playlists[0]["uri"]))
                    return f"▶️ Spiele Playlist: *{playlists[0]['name']}*"
                return f"❓ Nichts gefunden für: _{query}_"
            else:
                await loop.run_in_executor(None, lambda: sp.start_playback())
                current = self._get_current(sp)
                return f"▶️ Wiedergabe gestartet{f': {current}' if current else ''}."
        except Exception as e:
            logger.error(f"Spotify-Play-Fehler: {e}")
            return f"❌ Spotify-Fehler: {e}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def pause(self, user_key: str) -> Optional[str]:
        sp = self._get_client(user_key)
        if not sp:
            return None
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: sp.pause_playback())
            return "⏸ Pause."
        except Exception as e:
            return f"❌ Fehler: {e}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def skip(self, user_key: str) -> Optional[str]:
        sp = self._get_client(user_key)
        if not sp:
            return None
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: sp.next_track())
            return "⏭ Nächster Titel."
        except Exception as e:
            return f"❌ Fehler: {e}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def current(self, user_key: str) -> Optional[str]:
        sp = self._get_client(user_key)
        if not sp:
            return None
        loop = asyncio.get_running_loop()
        try:
            playback = await loop.run_in_executor(None, lambda: sp.current_playback())
            if not playback or not playback.get("is_playing"):
                return "⏹ Aktuell wird nichts gespielt."
            track = playback.get("item", {})
            name = track.get("name", "?")
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            progress_ms = playback.get("progress_ms", 0)
            duration_ms = track.get("duration_ms", 1)
            progress = int(progress_ms / 1000)
            duration = int(duration_ms / 1000)
            return (
                f"🎵 *{name}*\n"
                f"👤 {artists}\n"
                f"⏱ {progress // 60}:{progress % 60:02d} / "
                f"{duration // 60}:{duration % 60:02d}"
            )
        except Exception as e:
            return f"❌ Fehler: {e}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def volume(self, user_key: str, level: int) -> Optional[str]:
        sp = self._get_client(user_key)
        if not sp:
            return None
        level = max(0, min(100, level))
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, lambda: sp.volume(level))
            return f"🔊 Lautstärke: {level}%"
        except Exception as e:
            return f"❌ Fehler: {e}"

    def _get_current(self, sp) -> str:
        try:
            playback = sp.current_playback()
            if playback and playback.get("item"):
                track = playback["item"]
                return f"*{track['name']}* – {track['artists'][0]['name']}"
        except Exception:
            pass
        return ""

    # =========================================================================
    # Token-Persistenz (DB)
    # =========================================================================

    def _save_token(self, user_key: str, token_info: dict):
        try:
            from src.services.database import UserProfile, get_db

            with get_db()() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if profile:
                    profile.spotify_token_json = json.dumps(token_info)
                    logger.info(f"Spotify-Token gespeichert für: {user_key}")
                else:
                    new_profile = UserProfile(
                        user_key=user_key,
                        spotify_token_json=json.dumps(token_info),
                    )
                    session.add(new_profile)
                    logger.info(f"Spotify-Token gespeichert (neues Profil) für: {user_key}")
        except Exception as e:
            logger.error(f"Spotify-Token-Speicher-Fehler: {e}")

    def _load_token(self, user_key: str) -> Optional[dict]:
        try:
            from src.services.database import UserProfile, get_db

            with get_db()() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if profile and profile.spotify_token_json:
                    return json.loads(profile.spotify_token_json)
        except Exception as e:
            logger.warning(f"Spotify-Token-Laden-Fehler: {e}")
        return None
