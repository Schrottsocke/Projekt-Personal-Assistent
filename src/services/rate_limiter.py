"""
Rate Limiter: Schützt vor Nachrichten-Flooding und API-Credit-Drain.

Verwendet ein Sliding-Window-Verfahren (kein Token-Bucket):
Für jede Nachricht wird geprüft, wie viele Nachrichten in den letzten
N Sekunden von diesem User gesendet wurden.

Grenzen:
- 20 Nachrichten pro Minute  (Burst-Schutz)
- 300 Nachrichten pro Tag     (Credit-Schutz)

Da nur 2 autorisierte User existieren, reicht ein einfacher
In-Memory-Store mit Collections.deque. Kein externer Cache nötig.
"""

import logging
from collections import deque, defaultdict
from datetime import datetime, timedelta
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)

# Grenzen
RATE_LIMIT_MINUTE = 20  # max Nachrichten pro Minute
RATE_LIMIT_DAY = 300  # max Nachrichten pro Tag


class RateLimiter:
    """
    Sliding-Window Rate Limiter pro user_key.
    Thread-safe genug für asyncio (single-threaded event loop).
    """

    def __init__(self):
        self.tz = pytz.timezone(settings.TIMEZONE)
        # Deques speichern Timestamps der letzten Nachrichten
        self._minute_windows: dict[str, deque] = defaultdict(deque)
        self._day_windows: dict[str, deque] = defaultdict(deque)

    def check(self, user_key: str) -> tuple[bool, str]:
        """
        Prüft ob der User innerhalb der Limits liegt.

        Returns:
            (True, "")           → Nachricht erlaubt
            (False, "Grund")     → Nachricht blockiert
        """
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
            logger.warning(f"Rate limit (Minute) überschritten für '{user_key}'.")
            return False, "minute"

        if len(day_q) >= RATE_LIMIT_DAY:
            logger.warning(f"Rate limit (Tag) überschritten für '{user_key}'.")
            return False, "day"

        # Timestamp registrieren
        minute_q.append(now)
        day_q.append(now)
        return True, ""

    def get_stats(self, user_key: str) -> dict:
        """Gibt aktuelle Nutzung zurück (für Debugging)."""
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
