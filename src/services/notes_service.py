"""
Notizen-Service: CRUD für private und geteilte Notizen.
"""

import logging

logger = logging.getLogger(__name__)


class NotesService:
    def __init__(self):
        self._db = None

    def _ensure_initialized(self):
        if self._db is None:
            raise RuntimeError("NotesService not initialized – call initialize() first")

    async def initialize(self):
        from src.services.database import get_db, init_db

        init_db()
        self._db = get_db()
        logger.info("Notes Service initialisiert.")

    async def create_note(self, user_key: str, content: str, is_shared: bool = False) -> dict:
        from src.services.database import Note

        self._ensure_initialized()
        with self._db() as session:
            note = Note(
                user_key=user_key,
                content=content,
                is_shared=is_shared,
            )
            session.add(note)
            session.flush()
            result = {"id": note.id, "content": content, "is_shared": is_shared}
        logger.info(f"Notiz erstellt für '{user_key}': {content[:50]}...")
        return result

    async def get_notes(self, user_key: str, include_shared: bool = True) -> list[dict]:
        from src.services.database import Note

        self._ensure_initialized()
        with self._db() as session:
            query = session.query(Note)
            if include_shared:
                query = query.filter((Note.user_key == user_key) | (Note.is_shared == True))
            else:
                query = query.filter(Note.user_key == user_key)

            notes = query.order_by(Note.created_at.desc()).limit(50).all()
            return [
                {
                    "id": n.id,
                    "content": n.content,
                    "is_shared": n.is_shared,
                    "user_key": n.user_key,
                    "created_at": n.created_at,
                }
                for n in notes
            ]

    async def delete_note(self, note_id: int, user_key: str) -> bool:
        from src.services.database import Note

        self._ensure_initialized()
        with self._db() as session:
            note = session.query(Note).filter_by(id=note_id, user_key=user_key).first()
            if note:
                session.delete(note)
                return True
        return False
