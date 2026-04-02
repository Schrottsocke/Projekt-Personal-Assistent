"""Inbox Service: Zentrale Aktions-Inbox fuer Vorschlaege, Freigaben und Folgeaktionen."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class InboxService:
    """Aggregiert Aktionen aus allen Modulen in einer zentralen Inbox."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "inbox"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("InboxService initialisiert.")

    async def list_items(self, user_key: str, status: str = "pending", category: str = None, limit: int = 50, offset: int = 0) -> list[dict]:
        items = await self._load(user_key)
        if status:
            items = [i for i in items if i.get("status") == status]
        if category:
            items = [i for i in items if i.get("category") == category]
        items.sort(key=lambda x: x.get("priority", 99))
        return items[offset:offset + limit]

    async def add_item(self, user_key: str, data: dict) -> dict:
        items = await self._load(user_key)
        data["id"] = str(uuid.uuid4())
        data.setdefault("status", "pending")
        data.setdefault("priority", 5)
        data["created_at"] = datetime.now().isoformat()
        items.append(data)
        await self._save(user_key, items)
        return data

    async def action_item(self, user_key: str, item_id: str, action: str) -> Optional[dict]:
        """Fuehrt eine Aktion auf einem Inbox-Item aus (approve, dismiss, snooze)."""
        items = await self._load(user_key)
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            return None
        if action == "approve":
            item["status"] = "approved"
        elif action == "dismiss":
            item["status"] = "dismissed"
        elif action == "snooze":
            item["status"] = "snoozed"
        item["actioned_at"] = datetime.now().isoformat()
        item["action"] = action
        await self._save(user_key, items)
        return item

    async def count_pending(self, user_key: str) -> int:
        items = await self._load(user_key)
        return sum(1 for i in items if i.get("status") == "pending")

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, data: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
