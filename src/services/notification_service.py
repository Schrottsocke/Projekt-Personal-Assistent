"""
Notification Service: Zentrale Benachrichtigungsverwaltung.
Speichert und verwaltet Systemereignisse, Warnungen, Erinnerungen.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

VALID_TYPES = ("reminder", "follow_up", "document", "inbox", "weather", "system")
VALID_STATUSES = ("new", "read", "completed", "hidden")


class NotificationService:
    def __init__(self):
        self._db = None

    def _ensure_initialized(self):
        if self._db is None:
            raise RuntimeError("NotificationService not initialized – call initialize() first")

    async def initialize(self):
        from src.services.database import get_db, init_db

        init_db()
        self._db = get_db()
        logger.info("Notification Service initialisiert.")

    async def create(
        self,
        user_key: str,
        type: str,
        title: str,
        message: Optional[str] = None,
        link: Optional[str] = None,
    ) -> dict:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            notif = Notification(
                user_key=user_key,
                type=type,
                title=title,
                message=message,
                link=link,
            )
            session.add(notif)
            session.flush()
            result = self._to_dict(notif)
        logger.info("Notification #%d erstellt fuer '%s': %s", result["id"], user_key, title[:60])
        return result

    async def list(
        self,
        user_key: str,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            q = session.query(Notification).filter(Notification.user_key == user_key)
            if type_filter:
                q = q.filter(Notification.type == type_filter)
            if status_filter:
                q = q.filter(Notification.status == status_filter)
            else:
                # Default: versteckte ausblenden
                q = q.filter(Notification.status != "hidden")
            notifications = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
            return [self._to_dict(n) for n in notifications]

    async def count_unread(self, user_key: str) -> int:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            return (
                session.query(Notification)
                .filter(Notification.user_key == user_key, Notification.status == "new")
                .count()
            )

    async def update_status(self, notif_id: int, user_key: str, new_status: str) -> Optional[dict]:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            notif = session.query(Notification).filter_by(id=notif_id, user_key=user_key).first()
            if not notif:
                return None
            notif.status = new_status
            notif.updated_at = datetime.now(timezone.utc)
            return self._to_dict(notif)

    async def bulk_update_status(self, ids: list[int], user_key: str, new_status: str) -> int:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            count = (
                session.query(Notification)
                .filter(Notification.id.in_(ids), Notification.user_key == user_key)
                .update({Notification.status: new_status, Notification.updated_at: datetime.now(timezone.utc)},
                        synchronize_session="fetch")
            )
            return count

    async def mark_all_read(self, user_key: str) -> int:
        from src.services.database import Notification

        self._ensure_initialized()
        with self._db() as session:
            count = (
                session.query(Notification)
                .filter(Notification.user_key == user_key, Notification.status == "new")
                .update({Notification.status: "read", Notification.updated_at: datetime.now(timezone.utc)},
                        synchronize_session="fetch")
            )
            return count

    def _to_dict(self, notif) -> dict:
        return {
            "id": notif.id,
            "user_key": notif.user_key,
            "type": notif.type,
            "title": notif.title,
            "message": notif.message or "",
            "status": notif.status,
            "link": notif.link,
            "created_at": notif.created_at,
            "updated_at": notif.updated_at,
        }
