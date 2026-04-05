"""Scheduler-Job: Ueberfaellige Rechnungen markieren und benachrichtigen."""

import asyncio
import logging
from datetime import date

logger = logging.getLogger(__name__)


async def check_overdue_invoices():
    """Daily 08:00 - markiert ueberfaellige Rechnungen und benachrichtigt User."""
    try:
        from src.services.database import FinanceInvoice, UserProfile, get_db
        from src.services.notification_service import NotificationService

        today = date.today()

        def _mark_overdue():
            with get_db()() as session:
                invoices = (
                    session.query(FinanceInvoice, UserProfile.user_key)
                    .join(UserProfile, FinanceInvoice.user_id == UserProfile.id)
                    .filter(
                        FinanceInvoice.status == "open",
                        FinanceInvoice.due_date < today,
                    )
                    .all()
                )
                results = []
                for inv, user_key in invoices:
                    inv.status = "overdue"
                    results.append(
                        {
                            "id": inv.id,
                            "recipient": inv.recipient,
                            "total": inv.total,
                            "due_date": inv.due_date.isoformat() if inv.due_date else "",
                            "invoice_number": inv.invoice_number,
                            "user_key": user_key,
                        }
                    )
                return results

        overdue = await asyncio.to_thread(_mark_overdue)

        if not overdue:
            logger.info("Overdue-Invoice-Check: keine ueberfaelligen Rechnungen.")
            return

        notif_svc = NotificationService()
        await notif_svc.initialize()

        for inv in overdue:
            await notif_svc.create(
                user_key=inv["user_key"],
                type="document",
                title=f"Rechnung ueberfaellig: {inv['recipient']}",
                message=(
                    f"Rechnung{' ' + inv['invoice_number'] if inv['invoice_number'] else ''}"
                    f" ueber {inv['total']:.2f} EUR"
                    f" war faellig am {inv['due_date']}."
                ),
                link="#/invoices",
            )

        logger.info("Overdue-Invoice-Check: %d Rechnungen als ueberfaellig markiert.", len(overdue))
    except Exception as e:
        logger.error("Overdue-Invoice-Check-Fehler: %s", e, exc_info=True)
