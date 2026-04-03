"""Template Service: Wiederverwendbare Inhaltsbausteine (Vorlagen & Routinen)."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

STARTER_TEMPLATES = [
    {
        "name": "Wocheneinkauf Basics",
        "category": "shopping",
        "description": "Grundnahrungsmittel fuer die Woche",
        "is_starter": True,
        "content": {
            "items": [
                {"name": "Milch", "quantity": "1", "unit": "l"},
                {"name": "Brot", "quantity": "1", "unit": "stk"},
                {"name": "Eier", "quantity": "10", "unit": "stk"},
                {"name": "Butter", "quantity": "250", "unit": "g"},
                {"name": "Bananen", "quantity": "5", "unit": "stk"},
                {"name": "Nudeln", "quantity": "500", "unit": "g"},
                {"name": "Reis", "quantity": "500", "unit": "g"},
            ],
        },
    },
    {
        "name": "Morgenroutine",
        "category": "routine",
        "description": "Strukturierter Start in den Tag",
        "is_starter": True,
        "content": {
            "steps": [
                {"name": "Wasser trinken", "description": "Ein grosses Glas Wasser"},
                {"name": "Stretching", "description": "5 Minuten dehnen"},
                {"name": "Fruehstueck", "description": "Gesund fruehstuecken"},
                {"name": "Tagesplanung", "description": "Top 3 Aufgaben festlegen"},
                {"name": "E-Mails checken", "description": "Kurzer Ueberblick, nicht vertiefen"},
            ],
            "schedule": {"type": "daily", "time": "07:00"},
        },
    },
    {
        "name": "Wochenplanung Sonntag",
        "category": "checklist",
        "description": "Wochenstart vorbereiten",
        "is_starter": True,
        "content": {
            "items": [
                "Kalender fuer die Woche pruefen",
                "Einkaufsliste schreiben",
                "Mealplan fuer die Woche erstellen",
                "Offene Aufgaben priorisieren",
                "Kleidung fuer die Woche vorbereiten",
            ],
        },
    },
    {
        "name": "Putz-Checkliste",
        "category": "checklist",
        "description": "Woechentlicher Hausputz",
        "is_starter": True,
        "content": {
            "items": [
                "Kueche: Oberflaechen wischen",
                "Bad: Waschbecken und Toilette reinigen",
                "Wohnzimmer: Staubsaugen",
                "Schlafzimmer: Bettzeug wechseln",
                "Flur: Boden wischen",
                "Muell rausbringen",
            ],
        },
    },
    {
        "name": "Schnelles Abendessen",
        "category": "mealplan",
        "description": "Einfaches Pasta-Gericht fuer unter der Woche",
        "is_starter": True,
        "content": {
            "recipe_title": "Pasta Aglio e Olio",
            "meal_type": "dinner",
            "servings": 2,
            "notes": "20 Minuten, nur Grundzutaten noetig",
        },
    },
]


class TemplateService:
    """Verwaltet wiederverwendbare Vorlagen fuer Einkaufslisten, Nachrichten, Tasks etc."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "templates"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("TemplateService initialisiert.")

    async def list_templates(self, user_key: str, category: str = None, limit: int = 50, offset: int = 0) -> list[dict]:
        templates = await self._load(user_key)
        if not templates:
            templates = await self._seed_starters(user_key)
        if category:
            templates = [t for t in templates if t.get("category") == category]
        return templates[offset : offset + limit]

    async def get_template(self, user_key: str, template_id: str) -> Optional[dict]:
        templates = await self._load(user_key)
        if not templates:
            templates = await self._seed_starters(user_key)
        return next((t for t in templates if t.get("id") == template_id), None)

    async def create_template(self, user_key: str, data: dict) -> dict:
        templates = await self._load(user_key)
        if not templates:
            templates = await self._seed_starters(user_key)
        data["id"] = str(uuid.uuid4())
        data["created_at"] = datetime.now().isoformat()
        data["use_count"] = 0
        data.setdefault("is_starter", False)
        templates.append(data)
        await self._save(user_key, templates)
        return data

    async def update_template(self, user_key: str, template_id: str, updates: dict) -> Optional[dict]:
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

    async def apply_template(self, user_key: str, template_id: str) -> Optional[dict]:
        """Wendet eine Vorlage an und erhoeht den Nutzungszaehler."""
        templates = await self._load(user_key)
        if not templates:
            templates = await self._seed_starters(user_key)
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

    async def _seed_starters(self, user_key: str) -> list[dict]:
        """Erzeugt Starter-Vorlagen fuer neue Nutzer."""
        now = datetime.now().isoformat()
        templates = []
        for starter in STARTER_TEMPLATES:
            tpl = {**starter, "id": str(uuid.uuid4()), "created_at": now, "use_count": 0}
            templates.append(tpl)
        await self._save(user_key, templates)
        logger.info("Starter-Vorlagen fuer '%s' erstellt (%d Stueck).", user_key, len(templates))
        return templates

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, data: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
