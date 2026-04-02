"""
BaseMemoryService: Gemeinsame Basis fuer Bot- und API-MemoryService.

Kapselt die mem0-Initialisierung, Suche und Speicherung.
Spezialisierungen (Bot/API) erben und erweitern diese Klasse.
"""

import asyncio
import hashlib
import logging
import threading
import time

from config.settings import settings

logger = logging.getLogger(__name__)


class _TTLCache:
    """Einfacher In-Memory TTL-Cache fuer Memory-Suchergebnisse."""

    def __init__(self, ttl_seconds: int = 300):
        self._store: dict[str, tuple] = {}  # key -> (value, expires_at)
        self._ttl = ttl_seconds

    def _make_key(self, user_id: str, query: str, limit: int) -> str:
        q_hash = hashlib.md5(f"{query.strip().lower()}:{limit}".encode()).hexdigest()[:12]
        return f"{user_id}:{q_hash}"

    def get(self, user_id: str, query: str, limit: int):
        key = self._make_key(user_id, query, limit)
        entry = self._store.get(key)
        if entry and time.monotonic() < entry[1]:
            return entry[0]
        if entry:
            del self._store[key]
        return None

    def set(self, user_id: str, query: str, limit: int, value) -> None:
        key = self._make_key(user_id, query, limit)
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate_user(self, user_id: str) -> None:
        """Alle Cache-Eintraege fuer einen User loeschen (nach Memory-Write)."""
        prefix = f"{user_id}:"
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]


class BaseMemoryService:
    """
    Gemeinsame Basis fuer persistentes Langzeitgedaechtnis via mem0.
    Unterstuetzt lokalen Modus (ChromaDB) und Cloud-Modus.
    """

    def __init__(self):
        self._memory = None
        self._available = False
        self._search_cache = _TTLCache(ttl_seconds=settings.MEMORY_CACHE_TTL_MINUTES * 60)

    async def initialize(self):
        """Initialisiert mem0. Kann in Subklassen erweitert werden."""
        await self._setup_mem0()
        logger.info("%s initialisiert.", self.__class__.__name__)

    async def _setup_mem0(self):
        try:
            from mem0 import Memory

            if settings.MEMORY_MODE == "cloud" and settings.MEM0_API_KEY:
                from mem0 import MemoryClient

                self._memory = MemoryClient(api_key=settings.MEM0_API_KEY)
                self._available = True
                logger.info("mem0: Cloud-Modus aktiv.")
            else:
                config = {
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "personal_assistant",
                            "path": str(settings.BASE_DIR / "data" / "chroma_db"),
                        },
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": "gpt-4o-mini",
                            "api_key": settings.OPENROUTER_API_KEY,
                            "openai_base_url": settings.OPENROUTER_BASE_URL,
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": "text-embedding-3-small",
                            "api_key": settings.OPENROUTER_API_KEY,
                            "openai_base_url": settings.OPENROUTER_BASE_URL,
                        },
                    },
                }
                self._memory = Memory.from_config(config)
                self._available = True
                logger.info("mem0: Lokaler Modus aktiv.")

        except ImportError:
            logger.warning("mem0 nicht installiert. Verwende einfaches Fallback-Gedaechtnis.")
            self._memory = SimpleFallbackMemory()
            self._available = True
        except Exception as e:
            logger.error("mem0-Setup-Fehler: %s. Verwende Fallback.", e)
            self._memory = SimpleFallbackMemory()
            self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # Schreiben
    # ------------------------------------------------------------------

    async def add_memory(self, user_key: str, content: str):
        """Fuegt eine einzelne Erinnerung hinzu (als User-Nachricht)."""
        if not self._available or not self._memory:
            return
        try:
            await asyncio.to_thread(
                self._memory.add,
                messages=[{"role": "user", "content": content}],
                user_id=user_key,
            )
            logger.debug("Memory hinzugefuegt fuer %s: %s...", user_key, content[:50])
            self._search_cache.invalidate_user(user_key)
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Memory-Add-Fehler: %s", e)

    async def add_messages(self, messages: list[dict], user_key: str) -> list[str]:
        """Fuegt mehrere Nachrichten hinzu. Gibt IDs zurueck."""
        if not self._available or not self._memory:
            return []
        try:
            result = await asyncio.to_thread(self._memory.add, messages, user_id=user_key)
            self._search_cache.invalidate_user(user_key)
            if isinstance(result, dict) and "results" in result:
                return [r.get("id", "") for r in result["results"]]
            return []
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Memory-AddMessages-Fehler: %s", e)
            return []

    # ------------------------------------------------------------------
    # Lesen
    # ------------------------------------------------------------------

    async def search_memories(self, user_key: str, query: str, limit: int = 5) -> list[dict]:
        """Semantische Suche nach relevanten Erinnerungen (mit TTL-Cache)."""
        if not self._available or not self._memory:
            return []

        cached = self._search_cache.get(user_key, query, limit)
        if cached is not None:
            logger.info("perf | phase=history_and_memory | result=cache_hit")
            return cached

        try:
            results = await asyncio.to_thread(self._memory.search, query=query, user_id=user_key, limit=limit)
            if isinstance(results, dict) and "results" in results:
                out = results["results"]
            elif isinstance(results, list):
                out = results
            else:
                out = []
            self._search_cache.set(user_key, query, limit, out)
            logger.info("perf | phase=history_and_memory | result=cache_miss")
            return out
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Memory-Search-Fehler: %s", e)
            return []

    async def get_all_memories(self, user_key: str) -> list[dict]:
        """Gibt alle gespeicherten Erinnerungen zurueck."""
        if not self._available or not self._memory:
            return []
        try:
            results = await asyncio.to_thread(self._memory.get_all, user_id=user_key)
            if isinstance(results, dict) and "results" in results:
                return results["results"]
            if isinstance(results, list):
                return results
            return []
        except (OSError, ValueError, RuntimeError) as e:
            logger.error("Memory-GetAll-Fehler: %s", e)
            return []

    # ------------------------------------------------------------------
    # Loeschen
    # ------------------------------------------------------------------

    async def delete_memory(self, memory_id: str) -> bool:
        """Loescht eine einzelne Erinnerung anhand ihrer ID."""
        if not self._available or not self._memory:
            return False
        try:
            await asyncio.to_thread(self._memory.delete, memory_id)
            return True
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning("Memory-Delete-Fehler: %s", e)
            return False

    async def reset_user_memory(self, user_key: str) -> bool:
        """Loescht alle Erinnerungen eines Users."""
        if not self._available or not self._memory:
            return False
        try:
            await asyncio.to_thread(self._memory.delete_all, user_id=user_key)
            logger.info("Gedaechtnis fuer %s geloescht.", user_key)
            return True
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning("Memory-Reset-Fehler: %s", e)
            return False


class SimpleFallbackMemory:
    """
    Einfaches In-Memory Fallback, falls mem0 nicht verfuegbar.
    Daten gehen beim Neustart verloren.
    """

    def __init__(self):
        self._store: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def add(self, messages: list[dict], user_id: str):
        import uuid

        with self._lock:
            if user_id not in self._store:
                self._store[user_id] = []
            results = []
            for msg in messages:
                if msg.get("role") == "user":
                    self._store[user_id].append(msg["content"])
                    results.append({"id": str(uuid.uuid4()), "memory": msg["content"]})
        return {"results": results}

    def search(self, query: str, user_id: str, limit: int = 5) -> list[dict]:
        with self._lock:
            memories = list(self._store.get(user_id, []))
        query_lower = query.lower()
        matches = [m for m in memories if any(w in m.lower() for w in query_lower.split())]
        return [{"memory": m} for m in matches[:limit]]

    def get_all(self, user_id: str) -> list[dict]:
        with self._lock:
            memories = list(self._store.get(user_id, []))
        return [{"memory": m} for m in memories]

    def delete(self, memory_id: str):
        pass

    def delete_all(self, user_id: str):
        with self._lock:
            if user_id in self._store:
                del self._store[user_id]
