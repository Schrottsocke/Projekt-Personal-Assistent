"""Scheduler-Job: Dokumenten-Fristen pruefen."""

import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


async def check_document_deadlines():
    """Daily 07:30 - warnt vor anstehenden Dokumenten-Fristen (naechste 14 Tage)."""
    try:
        from src.services.database import HouseholdDocument, UserProfile, get_db
        from src.services.notification_service import NotificationService

        today = date.today()
        horizon = today + timedelta(days=14)

        def _query_documents():
            with get_db()() as session:
                docs = (
                    session.query(HouseholdDocument, UserProfile.user_key)
                    .join(UserProfile, HouseholdDocument.user_id == UserProfile.id)
                    .filter(
                        HouseholdDocument.deadline_date <= horizon,
                        HouseholdDocument.deadline_date >= today,
                    )
                    .all()
                )
                results = []
                for doc, user_key in docs:
                    results.append({
                        "id": doc.id,
                        "title": doc.title,
                        "category": doc.category,
                        "deadline_date": doc.deadline_date.isoformat() if doc.deadline_date else "",
                        "issuer": doc.issuer,
                        "user_key": user_key,
                    })
                return results

        upcoming = await asyncio.to_thread(_query_documents)

        if not upcoming:
            logger.info("Document-Deadline-Check: keine anstehenden Fristen.")
            return

        notif_svc = NotificationService()
        await notif_svc.initialize()

        for doc in upcoming:
            days_left = (date.fromisoformat(doc["deadline_date"]) - today).days
            label = f"{days_left} Tag{'e' if days_left != 1 else ''}"
            await notif_svc.create(
                user_key=doc["user_key"],
                type="document",
                title=f"Dokument-Frist: {doc['title']}",
                message=(
                    f"'{doc['title']}'"
                    f"{' von ' + doc['issuer'] if doc['issuer'] else ''}"
                    f" - Frist in {label} ({doc['deadline_date']})."
                ),
                link="#/documents",
            )

        logger.info("Document-Deadline-Check: %d Benachrichtigungen erstellt.", len(upcoming))
    except Exception as e:
        logger.error("Document-Deadline-Check-Fehler: %s", e, exc_info=True)
