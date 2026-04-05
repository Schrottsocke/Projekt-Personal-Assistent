"""Scheduler-Job: Faellige Haushaltsroutinen pruefen."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def check_routine_reminders():
    """Daily 09:00 - erinnert an faellige Haushaltsroutinen."""
    try:
        from src.services.database import Routine, RoutineCompletion, UserProfile, get_db
        from src.services.notification_service import NotificationService

        today = date.today()

        def _query_due_routines():
            with get_db()() as session:
                routines = (
                    session.query(Routine, UserProfile.user_key)
                    .join(UserProfile, Routine.current_assignee_id == UserProfile.id)
                    .all()
                )
                results = []
                for routine, user_key in routines:
                    # Find last completion
                    last = (
                        session.query(RoutineCompletion)
                        .filter(RoutineCompletion.routine_id == routine.id)
                        .order_by(RoutineCompletion.completed_at.desc())
                        .first()
                    )
                    last_date = last.completed_at.date() if last else None

                    is_due = False
                    if last_date is None:
                        # Never completed -> due
                        is_due = True
                    elif routine.interval == "daily":
                        is_due = last_date < today
                    elif routine.interval == "weekly":
                        is_due = last_date <= today - timedelta(days=7)
                    elif routine.interval == "monthly":
                        is_due = last_date <= today - timedelta(days=30)

                    if is_due:
                        results.append({
                            "id": routine.id,
                            "name": routine.name,
                            "interval": routine.interval,
                            "user_key": user_key,
                        })
                return results

        due_routines = await asyncio.to_thread(_query_due_routines)

        if not due_routines:
            logger.info("Routine-Reminder-Check: keine faelligen Routinen.")
            return

        notif_svc = NotificationService()
        await notif_svc.initialize()

        for r in due_routines:
            interval_label = {
                "daily": "taeglich",
                "weekly": "woechentlich",
                "monthly": "monatlich",
            }.get(r["interval"], r["interval"])
            await notif_svc.create(
                user_key=r["user_key"],
                type="reminder",
                title=f"Routine faellig: {r['name']}",
                message=f"Die {interval_label}e Routine '{r['name']}' ist faellig.",
                link="#/routines",
            )

        logger.info("Routine-Reminder-Check: %d Benachrichtigungen erstellt.", len(due_routines))
    except Exception as e:
        logger.error("Routine-Reminder-Check-Fehler: %s", e)
