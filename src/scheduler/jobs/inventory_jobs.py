"""Scheduler-Job: Ablaufende Garantien pruefen."""

import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


async def check_warranty_expiry():
    """Weekly Monday 07:00 - warnt vor ablaufenden Garantien (naechste 30 Tage)."""
    try:
        from src.services.database import UserProfile, Warranty, get_db
        from src.services.notification_service import NotificationService

        today = date.today()
        horizon = today + timedelta(days=30)

        def _query_warranties():
            with get_db()() as session:
                warranties = (
                    session.query(Warranty, UserProfile.user_key)
                    .join(UserProfile, Warranty.user_id == UserProfile.id)
                    .filter(
                        Warranty.warranty_end <= horizon,
                        Warranty.warranty_end > today,
                    )
                    .all()
                )
                results = []
                for w, user_key in warranties:
                    results.append(
                        {
                            "id": w.id,
                            "product_name": w.product_name,
                            "warranty_end": w.warranty_end.isoformat() if w.warranty_end else "",
                            "vendor": w.vendor,
                            "user_key": user_key,
                        }
                    )
                return results

        expiring = await asyncio.to_thread(_query_warranties)

        if not expiring:
            logger.info("Warranty-Expiry-Check: keine ablaufenden Garantien.")
            return

        notif_svc = NotificationService()
        await notif_svc.initialize()

        for w in expiring:
            days_left = (date.fromisoformat(w["warranty_end"]) - today).days
            await notif_svc.create(
                user_key=w["user_key"],
                type="reminder",
                title=f"Garantie laeuft ab: {w['product_name']}",
                message=(
                    f"Garantie fuer '{w['product_name']}'"
                    f"{' (' + w['vendor'] + ')' if w['vendor'] else ''}"
                    f" endet in {days_left} Tagen ({w['warranty_end']})."
                ),
                link="#/inventory",
            )

        logger.info("Warranty-Expiry-Check: %d Benachrichtigungen erstellt.", len(expiring))
    except Exception as e:
        logger.error("Warranty-Expiry-Check-Fehler: %s", e, exc_info=True)
