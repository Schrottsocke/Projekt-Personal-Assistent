"""Contacts Service: Personen-Kontext aus E-Mail, Kalender und Erinnerungen."""

import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class ContactsService:
    """Aggregiert Kontaktinformationen aus verschiedenen Quellen (E-Mail, Kalender)."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "contacts"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ContactsService initialisiert.")

    async def list_contacts(
        self, user_key: str, query: str = "", limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """Liste aller bekannten Kontakte mit optionalem Suchfilter."""
        contacts = await self._load_contacts(user_key)
        if query:
            q = query.lower()
            contacts = [
                c
                for c in contacts
                if q in c.get("name", "").lower() or q in c.get("email", "").lower()
            ]
        return contacts[offset : offset + limit]

    async def get_contact(self, user_key: str, contact_id: str) -> Optional[dict]:
        contacts = await self._load_contacts(user_key)
        return next((c for c in contacts if c.get("id") == contact_id), None)

    async def upsert_contact(self, user_key: str, contact_data: dict) -> dict:
        contacts = await self._load_contacts(user_key)
        existing = next(
            (c for c in contacts if c.get("id") == contact_data.get("id")), None
        )
        if existing:
            existing.update(contact_data)
            result = existing
        else:
            contact_data.setdefault("id", str(uuid.uuid4()))
            contacts.append(contact_data)
            result = contact_data
        await self._save_contacts(user_key, contacts)
        return result

    async def delete_contact(self, user_key: str, contact_id: str) -> bool:
        contacts = await self._load_contacts(user_key)
        before = len(contacts)
        contacts = [c for c in contacts if c.get("id") != contact_id]
        if len(contacts) < before:
            await self._save_contacts(user_key, contacts)
            return True
        return False

    async def _load_contacts(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save_contacts(self, user_key: str, contacts: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(contacts, ensure_ascii=False, indent=2))
