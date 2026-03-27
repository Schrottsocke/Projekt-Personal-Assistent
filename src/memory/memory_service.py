"""
Memory Service: Persistent Langzeitgedächtnis via mem0.
Speichert nutzerspezifische Infos (privat + geteilt).
"""

import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Wrapper um mem0 für persistentes Langzeitgedächtnis.
    Unterstützt lokalen Modus (SQLite/ChromaDB) und Cloud-Modus.
    """

    def __init__(self):
        self._memory = None
        self._db = None  # SQLite für Onboarding-Status und geteilte Daten

    async def initialize(self):
        """Initialisiert mem0 und die lokale DB."""
        await self._setup_mem0()
        await self._setup_db()
        logger.info("Memory Service initialisiert.")

    async def _setup_mem0(self):
        try:
            from mem0 import Memory

            if settings.MEMORY_MODE == "cloud" and settings.MEM0_API_KEY:
                from mem0 import MemoryClient
                self._memory = MemoryClient(api_key=settings.MEM0_API_KEY)
                logger.info("mem0: Cloud-Modus aktiv.")
            else:
                # Lokaler Modus: ChromaDB + SQLite
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
                logger.info("mem0: Lokaler Modus aktiv.")

        except ImportError:
            logger.warning("mem0 nicht installiert. Verwende einfaches Fallback-Gedächtnis.")
            self._memory = SimpleFallbackMemory()
        except Exception as e:
            logger.error(f"mem0-Setup-Fehler: {e}. Verwende Fallback.")
            self._memory = SimpleFallbackMemory()

    async def _setup_db(self):
        from src.services.database import get_db
        self._db = get_db()

    async def add_memory(self, user_key: str, content: str):
        """Fügt eine neue Erinnerung zum Gedächtnis hinzu."""
        try:
            self._memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_key,
            )
            logger.debug(f"Memory hinzugefügt für {user_key}: {content[:50]}...")
        except Exception as e:
            logger.error(f"Memory-Add-Fehler: {e}")

    async def search_memories(self, user_key: str, query: str, limit: int = 5) -> list[dict]:
        """Sucht relevante Erinnerungen für eine Anfrage."""
        try:
            results = self._memory.search(query=query, user_id=user_key, limit=limit)
            # mem0 gibt je nach Version unterschiedliche Formate zurück
            if isinstance(results, dict) and "results" in results:
                return results["results"]
            if isinstance(results, list):
                return results
            return []
        except Exception as e:
            logger.error(f"Memory-Search-Fehler: {e}")
            return []

    async def get_all_memories(self, user_key: str) -> list[dict]:
        """Gibt alle gespeicherten Erinnerungen zurück."""
        try:
            results = self._memory.get_all(user_id=user_key)
            if isinstance(results, dict) and "results" in results:
                return results["results"]
            if isinstance(results, list):
                return results
            return []
        except Exception as e:
            logger.error(f"Memory-GetAll-Fehler: {e}")
            return []

    async def add_conversation_turn(
        self, user_key: str, user_message: str, assistant_response: str
    ):
        """Speichert einen Gesprächsaustausch im Gedächtnis."""
        try:
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response},
            ]
            self._memory.add(messages=messages, user_id=user_key)
        except Exception as e:
            logger.error(f"Conversation-Memory-Fehler: {e}")

    async def upsert_fact(self, user_key: str, content: str):
        """
        Speichert einen Fakt mit Bestätigungs-Tracking (JARVIS Continuous Learning).
        Wenn der Fakt bereits existiert, wird confirmation_count erhöht.
        """
        try:
            from src.services.database import MemoryFact
            from datetime import datetime
            with self._db() as session:
                existing = session.query(MemoryFact).filter_by(
                    user_key=user_key, content=content
                ).first()
                if existing:
                    existing.confirmation_count += 1
                    existing.last_used = datetime.utcnow()
                else:
                    session.add(MemoryFact(user_key=user_key, content=content))
        except Exception as e:
            logger.error(f"Upsert-Fact-Fehler: {e}")

    async def get_top_facts(self, user_key: str, limit: int = 10) -> list[dict]:
        """Gibt die bestätigtesten Fakten sortiert nach Konfidenz zurück."""
        try:
            from src.services.database import MemoryFact
            with self._db() as session:
                facts = (
                    session.query(MemoryFact)
                    .filter_by(user_key=user_key)
                    .order_by(MemoryFact.confirmation_count.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": f.id,
                        "content": f.content,
                        "confirmation_count": f.confirmation_count,
                    }
                    for f in facts
                ]
        except Exception as e:
            logger.error(f"Get-Top-Facts-Fehler: {e}")
            return []

    async def mark_onboarded(self, user_key: str):
        """Markiert User als onboardet in der lokalen DB."""
        try:
            from src.services.database import UserProfile
            with self._db() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if not profile:
                    profile = UserProfile(user_key=user_key)
                    session.add(profile)
                profile.is_onboarded = True
                session.commit()
        except Exception as e:
            logger.error(f"Mark-Onboarded-Fehler: {e}")

    async def is_onboarded(self, user_key: str) -> bool:
        """Prüft ob User bereits onboardet wurde."""
        try:
            from src.services.database import UserProfile
            with self._db() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                return bool(profile and profile.is_onboarded)
        except Exception as e:
            logger.error(f"Is-Onboarded-Fehler: {e}")
            return False


class SimpleFallbackMemory:
    """
    Einfaches In-Memory Fallback, falls mem0 nicht verfügbar.
    Daten gehen beim Neustart verloren.
    """

    def __init__(self):
        self._store: dict[str, list[str]] = {}

    def add(self, messages: list[dict], user_id: str):
        if user_id not in self._store:
            self._store[user_id] = []
        for msg in messages:
            if msg.get("role") == "user":
                self._store[user_id].append(msg["content"])

    def search(self, query: str, user_id: str, limit: int = 5) -> list[dict]:
        memories = self._store.get(user_id, [])
        # Einfache Keyword-Suche
        query_lower = query.lower()
        matches = [m for m in memories if any(w in m.lower() for w in query_lower.split())]
        return [{"memory": m} for m in matches[:limit]]

    def get_all(self, user_id: str) -> list[dict]:
        memories = self._store.get(user_id, [])
        return [{"memory": m} for m in memories]
