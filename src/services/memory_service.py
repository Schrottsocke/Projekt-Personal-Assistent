"""
MemoryService: Persistentes Gedächtnis via mem0ai.

Speichert Fakten und Gesprächskontext pro User und ermöglicht
semantische Suche über alle gespeicherten Erinnerungen.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Wrapper um mem0ai für persistentes User-Gedächtnis.
    Speichert Fakten, Vorlieben und Kontext pro User.
    """

    def __init__(self):
        self._mem = None
        self._available = False

    async def initialize(self):
        """Initialisiert mem0. Fehler werden abgefangen – Service läuft dann ohne Gedächtnis."""
        try:
            from mem0 import Memory
            self._mem = Memory()
            self._available = True
            logger.info("MemoryService initialisiert (mem0).")
        except Exception as e:
            logger.warning(f"MemoryService: mem0 nicht verfügbar – {e}. Service läuft ohne Gedächtnis.")
            self._available = False

    # ------------------------------------------------------------------
    # Schreiben
    # ------------------------------------------------------------------

    async def add_memory(self, messages: list[dict], user_key: str) -> list[str]:
        """
        Fügt Nachrichten zum Gedächtnis hinzu.
        messages: Liste von {"role": "user"|"assistant", "content": "..."}
        Gibt IDs der gespeicherten Erinnerungen zurück.
        """
        if not self._available or not self._mem:
            return []
        try:
            result = self._mem.add(messages, user_id=user_key)
            ids = [r.get("id", "") for r in result.get("results", [])]
            logger.debug(f"MemoryService: {len(ids)} Erinnerung(en) gespeichert für {user_key}")
            return ids
        except Exception as e:
            logger.warning(f"MemoryService.add_memory Fehler: {e}")
            return []

    async def add_fact(self, fact: str, user_key: str) -> Optional[str]:
        """Speichert einen einzelnen Fakt als User-Nachricht."""
        if not self._available or not self._mem:
            return None
        try:
            result = self._mem.add(
                [{"role": "user", "content": fact}],
                user_id=user_key,
            )
            results = result.get("results", [])
            return results[0].get("id") if results else None
        except Exception as e:
            logger.warning(f"MemoryService.add_fact Fehler: {e}")
            return None

    # ------------------------------------------------------------------
    # Lesen
    # ------------------------------------------------------------------

    async def search_memories(self, query: str, user_key: str, limit: int = 5) -> list[dict]:
        """
        Semantische Suche nach relevanten Erinnerungen.
        Gibt Liste von {"memory": "...", "score": 0.0-1.0} zurück.
        """
        if not self._available or not self._mem:
            return []
        try:
            results = self._mem.search(query, user_id=user_key, limit=limit)
            return results.get("results", [])
        except Exception as e:
            logger.warning(f"MemoryService.search Fehler: {e}")
            return []

    async def get_all_memories(self, user_key: str) -> list[dict]:
        """
        Gibt alle gespeicherten Erinnerungen eines Users zurück.
        Gibt Liste von {"memory": "...", "id": "..."} zurück.
        """
        if not self._available or not self._mem:
            return []
        try:
            results = self._mem.get_all(user_id=user_key)
            return results.get("results", [])
        except Exception as e:
            logger.warning(f"MemoryService.get_all Fehler: {e}")
            return []

    # ------------------------------------------------------------------
    # Löschen
    # ------------------------------------------------------------------

    async def delete_memory(self, memory_id: str) -> bool:
        """Löscht eine einzelne Erinnerung anhand ihrer ID."""
        if not self._available or not self._mem:
            return False
        try:
            self._mem.delete(memory_id)
            return True
        except Exception as e:
            logger.warning(f"MemoryService.delete Fehler: {e}")
            return False

    async def reset_user_memory(self, user_key: str) -> bool:
        """Löscht alle Erinnerungen eines Users."""
        if not self._available or not self._mem:
            return False
        try:
            self._mem.delete_all(user_id=user_key)
            logger.info(f"MemoryService: Gedächtnis für {user_key} gelöscht.")
            return True
        except Exception as e:
            logger.warning(f"MemoryService.reset Fehler: {e}")
            return False

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._available
