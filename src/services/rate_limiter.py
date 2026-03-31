"""
Rate Limiter: Schützt vor Nachrichten-Flooding und API-Credit-Drain.

Verwendet ein Sliding-Window-Verfahren:
Für jede Nachricht wird geprüft, wie viele Nachrichten in den letzten
N Sekunden von diesem User gesendet wurden.

Grenzen:
- 20 Nachrichten pro Minute  (Burst-Schutz)
- 300 Nachrichten pro Tag     (Credit-Schutz)

Speicherung: SQLite-basiert (persistent über Neustarts).
Fallback: In-Memory deque falls SQLite nicht verfügbar ist.
"""

import logging
import sqlite3
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import pytz

from config.settings import settings

logger = logging.getLogger(__name__)

# Grenzen
RATE_LIMIT_MINUTE = 20  # max Nachrichten pro Minute
RATE_LIMIT_DAY = 300  # max Nachrichten pro Tag

# Alte Einträge nach 24h löschen
_CLEANUP_INTERVAL = 3600  # Sekunden zwischen Cleanup-Läufen

_DB_DIR = Path("data")
_DB_PATH = _DB_DIR / "rate_limits.db"


class RateLimiter:
    """
    Sliding-Window Rate Limiter pro user_key.
    Persistiert Timestamps in SQLite. Fällt auf In-Memory zurück bei DB-Fehlern.
    """

    def __init__(self):
        self.tz = pytz.timezone(settings.TIMEZONE)
        self._use_sqlite = False
        self._conn: sqlite3.Connection | None = None
        self._last_cleanup: float = 0.0

        # In-Memory Fallback
        self._minute_windows: dict[str, deque] = defaultdict(deque)
        self._day_windows: dict[str, deque] = defaultdict(deque)

        # SQLite initialisieren
        try:
            _DB_DIR.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_key TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    PRIMARY KEY (user_key, timestamp)
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_ts ON rate_limits (timestamp)")
            self._conn.commit()
            self._use_sqlite = True
            logger.info("RateLimiter: SQLite-Persistenz aktiv (%s)", _DB_PATH)
        except Exception as exc:
            logger.warning("RateLimiter: SQLite nicht verfuegbar (%s) – Fallback auf In-Memory.", exc)
            self._use_sqlite = False

    def _cleanup_old_entries(self) -> None:
        """Löscht Einträge älter als 24h (periodisch)."""
        now = time.time()
        if now - self._last_cleanup < _CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        try:
            cutoff = now - 86400  # 24h
            self._conn.execute("DELETE FROM rate_limits WHERE timestamp < ?", (cutoff,))
            self._conn.commit()
        except Exception as exc:
            logger.warning("RateLimiter: Cleanup fehlgeschlagen: %s", exc)

    def check(self, user_key: str) -> tuple[bool, str]:
        """
        Prüft ob der User innerhalb der Limits liegt.

        Returns:
            (True, "")           → Nachricht erlaubt
            (False, "Grund")     → Nachricht blockiert
        """
        if self._use_sqlite:
            return self._check_sqlite(user_key)
        return self._check_memory(user_key)

    def _check_sqlite(self, user_key: str) -> tuple[bool, str]:
        """SQLite-basierte Prüfung."""
        self._cleanup_old_entries()

        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400

        try:
            # Minute-Limit prüfen
            row = self._conn.execute(
                "SELECT COUNT(*) FROM rate_limits WHERE user_key = ? AND timestamp >= ?",
                (user_key, minute_ago),
            ).fetchone()
            minute_count = row[0] if row else 0

            if minute_count >= RATE_LIMIT_MINUTE:
                logger.warning("Rate limit (Minute) ueberschritten fuer '%s'.", user_key)
                return False, "minute"

            # Tages-Limit prüfen
            row = self._conn.execute(
                "SELECT COUNT(*) FROM rate_limits WHERE user_key = ? AND timestamp >= ?",
                (user_key, day_ago),
            ).fetchone()
            day_count = row[0] if row else 0

            if day_count >= RATE_LIMIT_DAY:
                logger.warning("Rate limit (Tag) ueberschritten fuer '%s'.", user_key)
                return False, "day"

            # Timestamp registrieren
            self._conn.execute(
                "INSERT OR IGNORE INTO rate_limits (user_key, timestamp) VALUES (?, ?)",
                (user_key, now),
            )
            self._conn.commit()
            return True, ""

        except Exception as exc:
            logger.warning("RateLimiter: SQLite-Fehler bei check() – Fallback auf erlaubt: %s", exc)
            return True, ""

    def _check_memory(self, user_key: str) -> tuple[bool, str]:
        """In-Memory Fallback-Prüfung (Original-Logik)."""
        now = datetime.now(self.tz)
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)

        minute_q = self._minute_windows[user_key]
        day_q = self._day_windows[user_key]

        # Alte Einträge aus dem Fenster entfernen
        while minute_q and minute_q[0] < minute_ago:
            minute_q.popleft()
        while day_q and day_q[0] < day_ago:
            day_q.popleft()

        # Limits prüfen
        if len(minute_q) >= RATE_LIMIT_MINUTE:
            logger.warning("Rate limit (Minute) ueberschritten fuer '%s'.", user_key)
            return False, "minute"

        if len(day_q) >= RATE_LIMIT_DAY:
            logger.warning("Rate limit (Tag) ueberschritten fuer '%s'.", user_key)
            return False, "day"

        # Timestamp registrieren
        minute_q.append(now)
        day_q.append(now)
        return True, ""

    def get_stats(self, user_key: str) -> dict:
        """Gibt aktuelle Nutzung zurück (für Debugging)."""
        if self._use_sqlite:
            return self._get_stats_sqlite(user_key)
        return self._get_stats_memory(user_key)

    def _get_stats_sqlite(self, user_key: str) -> dict:
        """SQLite-basierte Stats."""
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 86400

        try:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM rate_limits WHERE user_key = ? AND timestamp >= ?",
                (user_key, minute_ago),
            ).fetchone()
            minute_count = row[0] if row else 0

            row = self._conn.execute(
                "SELECT COUNT(*) FROM rate_limits WHERE user_key = ? AND timestamp >= ?",
                (user_key, day_ago),
            ).fetchone()
            day_count = row[0] if row else 0
        except Exception:
            minute_count = -1
            day_count = -1

        return {
            "user_key": user_key,
            "last_minute": minute_count,
            "limit_minute": RATE_LIMIT_MINUTE,
            "last_day": day_count,
            "limit_day": RATE_LIMIT_DAY,
        }

    def _get_stats_memory(self, user_key: str) -> dict:
        """In-Memory Fallback-Stats."""
        now = datetime.now(self.tz)
        minute_ago = now - timedelta(minutes=1)
        day_ago = now - timedelta(days=1)

        minute_count = sum(1 for t in self._minute_windows[user_key] if t >= minute_ago)
        day_count = sum(1 for t in self._day_windows[user_key] if t >= day_ago)
        return {
            "user_key": user_key,
            "last_minute": minute_count,
            "limit_minute": RATE_LIMIT_MINUTE,
            "last_day": day_count,
            "limit_day": RATE_LIMIT_DAY,
        }


# Singleton – einmal erstellt, von allen Handlern geteilt
rate_limiter = RateLimiter()
