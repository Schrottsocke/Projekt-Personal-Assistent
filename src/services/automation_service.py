"""Automation Service: Regel- und Automationscenter fuer bereichsuebergreifende Workflows."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class AutomationService:
    """Verwaltet benutzerdefinierte Automatisierungsregeln (wenn X dann Y)."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "automations"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("AutomationService initialisiert.")

    async def list_rules(
        self, user_key: str, active_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        rules = await self._load(user_key)
        if active_only:
            rules = [r for r in rules if r.get("active", True)]
        return rules[offset : offset + limit]

    async def create_rule(self, user_key: str, data: dict) -> dict:
        rules = await self._load(user_key)
        data["id"] = str(uuid.uuid4())
        data.setdefault("active", True)
        data["created_at"] = datetime.now().isoformat()
        data["trigger_count"] = 0
        rules.append(data)
        await self._save(user_key, rules)
        return data

    async def update_rule(self, user_key: str, rule_id: str, updates: dict) -> Optional[dict]:
        rules = await self._load(user_key)
        rule = next((r for r in rules if r.get("id") == rule_id), None)
        if not rule:
            return None
        rule.update(updates)
        rule["updated_at"] = datetime.now().isoformat()
        await self._save(user_key, rules)
        return rule

    async def toggle_rule(self, user_key: str, rule_id: str) -> Optional[dict]:
        rules = await self._load(user_key)
        rule = next((r for r in rules if r.get("id") == rule_id), None)
        if not rule:
            return None
        rule["active"] = not rule.get("active", True)
        await self._save(user_key, rules)
        return rule

    async def delete_rule(self, user_key: str, rule_id: str) -> bool:
        rules = await self._load(user_key)
        before = len(rules)
        rules = [r for r in rules if r.get("id") != rule_id]
        if len(rules) < before:
            await self._save(user_key, rules)
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
