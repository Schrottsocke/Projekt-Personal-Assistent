"""Template Service: Wiederverwendbare Inhaltsbausteine (Vorlagen & Routinen)."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class TemplateService:
    """Verwaltet wiederverwendbare Vorlagen fuer Einkaufslisten, Nachrichten, Tasks etc."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "templates"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("TemplateService initialisiert.")

    async def list_templates(
        self, user_key: str, category: str = None, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        templates = await self._load(user_key)
        if category:
            templates = [t for t in templates if t.get("category") == category]
        return templates[offset : offset + limit]

    async def get_template(self, user_key: str, template_id: str) -> Optional[dict]:
        templates = await self._load(user_key)
        return next((t for t in templates if t.get("id") == template_id), None)

    async def create_template(self, user_key: str, data: dict) -> dict:
        templates = await self._load(user_key)
        data["id"] = str(uuid.uuid4())
        data["created_at"] = datetime.now().isoformat()
        data["use_count"] = 0
        templates.append(data)
        await self._save(user_key, templates)
        return data

    async def update_template(
        self, user_key: str, template_id: str, updates: dict
    ) -> Optional[dict]:
        templates = await self._load(user_key)
        tpl = next((t for t in templates if t.get("id") == template_id), None)
        if not tpl:
            return None
        for key, val in updates.items():
            if val is not None:
                tpl[key] = val
        tpl["updated_at"] = datetime.now().isoformat()
        await self._save(user_key, templates)
        return tpl

    async def apply_template(
        self, user_key: str, template_id: str
    ) -> Optional[dict]:
        """Wendet eine Vorlage an und erhoeht den Nutzungszaehler."""
        templates = await self._load(user_key)
        tpl = next((t for t in templates if t.get("id") == template_id), None)
        if not tpl:
            return None
        tpl["use_count"] = tpl.get("use_count", 0) + 1
        tpl["last_used"] = datetime.now().isoformat()
        await self._save(user_key, templates)
        return tpl

    async def delete_template(self, user_key: str, template_id: str) -> bool:
        templates = await self._load(user_key)
        before = len(templates)
        templates = [t for t in templates if t.get("id") != template_id]
        if len(templates) < before:
            await self._save(user_key, templates)
            return True
        return False

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, data: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
