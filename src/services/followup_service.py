"""Follow-up Service: Tracks unanswered emails and open commitments."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class FollowUpService:
    """Verwaltet Follow-ups fuer unbeantwortete E-Mails und offene Zusagen."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "followups"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("FollowUpService initialisiert.")

    async def list_followups(
        self, user_key: str, status: str = "open", limit: int = 50, offset: int = 0
    ) -> list[dict]:
        followups = await self._load(user_key)
        if status:
            followups = [f for f in followups if f.get("status") == status]
        followups.sort(key=lambda f: f.get("due_date", "9999"), reverse=False)
        return followups[offset : offset + limit]

    async def create_followup(self, user_key: str, data: dict) -> dict:
        followups = await self._load(user_key)
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("status", "open")
        data.setdefault("created_at", datetime.now().isoformat())
        followups.append(data)
        await self._save(user_key, followups)
        return data

    async def update_followup(
        self, user_key: str, followup_id: str, updates: dict
    ) -> Optional[dict]:
        followups = await self._load(user_key)
        item = next((f for f in followups if f.get("id") == followup_id), None)
        if not item:
            return None
        item.update(updates)
        item["updated_at"] = datetime.now().isoformat()
        await self._save(user_key, followups)
        return item

    async def get_due_followups(self, user_key: str) -> list[dict]:
        """Gibt alle faelligen Follow-ups zurueck (due_date <= heute)."""
        followups = await self._load(user_key)
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            f
            for f in followups
            if f.get("status") == "open" and f.get("due_date", "9999") <= today
        ]

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, data: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
