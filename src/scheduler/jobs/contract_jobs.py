"""Scheduler-Job: Vertragskuendigungsfristen pruefen."""

import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

THRESHOLDS_DAYS = [30, 14, 7, 1]


async def check_contract_deadlines():
    """Daily 07:00 - prueft Vertraege mit nahender Kuendigungsfrist."""
    try:
        from src.services.database import Contract, UserProfile, get_db
        from src.services.notification_service import NotificationService

        today = date.today()
        notifications_created = 0

        def _query_contracts():
            with get_db()() as session:
                contracts = (
                    session.query(Contract, UserProfile.user_key)
                    .join(UserProfile, Contract.user_id == UserProfile.id)
                    .filter(Contract.status == "active")
                    .all()
                )
                results = []
                for contract, user_key in contracts:
                    results.append({
                        "id": contract.id,
                        "name": contract.name,
                        "provider": contract.provider,
                        "cancellation_deadline": contract.cancellation_deadline,
                        "next_billing": contract.next_billing,
                        "cancellation_days": contract.cancellation_days,
                        "user_key": user_key,
                    })
                return results

        contracts = await asyncio.to_thread(_query_contracts)

        notif_svc = NotificationService()
        await notif_svc.initialize()

        for c in contracts:
            # Calculate effective deadline
            deadline_date = c["cancellation_deadline"]
            if not deadline_date and c["next_billing"]:
                cancel_days = c["cancellation_days"] or 30
                deadline_date = c["next_billing"] - timedelta(days=cancel_days)

            if not deadline_date:
                continue

            days_remaining = (deadline_date - today).days

            for threshold in THRESHOLDS_DAYS:
                if days_remaining == threshold:
                    label = f"{threshold} Tag{'e' if threshold != 1 else ''}"
                    await notif_svc.create(
                        user_key=c["user_key"],
                        type="reminder",
                        title=f"Kuendigungsfrist: {c['name']}",
                        message=(
                            f"Vertrag '{c['name']}'"
                            f"{' bei ' + c['provider'] if c['provider'] else ''}"
                            f" - Kuendigungsfrist in {label} ({deadline_date.isoformat()})."
                        ),
                        link="#/contracts",
                    )
                    notifications_created += 1
                    break

        logger.info("Contract-Deadline-Check: %d Benachrichtigungen erstellt.", notifications_created)
    except Exception as e:
        logger.error("Contract-Deadline-Check-Fehler: %s", e, exc_info=True)
