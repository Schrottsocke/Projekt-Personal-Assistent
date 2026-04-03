"""
ApiMemoryService: API-spezifisches Gedaechtnis (FastAPI).

Erweitert BaseMemoryService um:
- add_fact(): Einzelnen Fakt als User-Nachricht speichern, ID zurueckgeben
- Alle Delete-Operationen (delete_memory, reset_user_memory) sind in der Basis

Nutzt dieselbe mem0-Instanz und ChromaDB wie der Bot.
"""

import logging
from typing import Optional
from src.memory.base_memory_service import BaseMemoryService

logger = logging.getLogger(__name__)


class ApiMemoryService(BaseMemoryService):
    """
    Memory Service fuer die FastAPI-App.
    Erbt mem0-Logik von BaseMemoryService, fuegt API-spezifische Methoden hinzu.
    """

    async def add_fact(self, fact: str, user_key: str) -> Optional[str]:
        """Speichert einen einzelnen Fakt als User-Nachricht. Gibt die ID zurueck."""
        ids = await self.add_messages(
            messages=[{"role": "user", "content": fact}],
            user_key=user_key,
        )
        return ids[0] if ids else None
