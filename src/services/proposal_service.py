"""
Proposal Service: Human-in-the-Loop Genehmigungssystem.

Ablauf:
  Vorschlag erstellen → Telegram-Nachricht mit ✅/❌ Buttons
  → User klickt → Aktion ausführen oder ablehnen
"""

import json
import logging
from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config.settings import settings

logger = logging.getLogger(__name__)

# Proposal-Typen
TYPE_CALENDAR_CREATE = "calendar_create"
TYPE_REMINDER_CREATE = "reminder_create"
TYPE_NOTE_CREATE = "note_create"
TYPE_TASK_CREATE = "task_create"
TYPE_AI_SUGGESTION = "ai_suggestion"
TYPE_SHARED_ACTION = "shared_action"

# Status
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# Emoji-Mapping für Typen
TYPE_ICONS = {
    TYPE_CALENDAR_CREATE: "📅",
    TYPE_REMINDER_CREATE: "⏰",
    TYPE_NOTE_CREATE: "📝",
    TYPE_TASK_CREATE: "📋",
    TYPE_AI_SUGGESTION: "🤖",
    TYPE_SHARED_ACTION: "🔗",
}


class ProposalService:
    """
    Verwaltet Vorschläge beider Bots.
    Wird einmalig in main.py erstellt und in beide Bots injiziert.
    """

    def __init__(self):
        self._db = None
        # user_key → telegram Application (für Bot-übergreifende Proposals)
        self._apps: dict = {}

    async def initialize(self):
        from src.services.database import get_db, init_db
        init_db()
        self._db = get_db()
        logger.info("Proposal Service initialisiert.")

    def register_app(self, user_key: str, app):
        """Registriert eine Telegram-Application für einen User."""
        self._apps[user_key] = app

    def _get_auto_approve_types(self, user_key: str) -> set:
        """Liest die auto_approve_types eines Users aus der DB."""
        try:
            from src.services.database import UserProfile
            with self._db() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if profile and profile.auto_approve_types:
                    return set(t.strip() for t in profile.auto_approve_types.split(",") if t.strip())
        except Exception as e:
            logger.warning(f"Auto-Approve-Types Lesefehler: {e}")
        return {"timer_create"}  # Fallback: Timer immer auto-approve

    async def create_proposal(
        self,
        user_key: str,
        proposal_type: str,
        title: str,
        payload: dict,
        created_by: str,
        chat_id: str,
        description: str = "",
        bot=None,
    ) -> Optional[dict]:
        """
        Erstellt einen neuen Vorschlag.
        Wenn der Typ in auto_approve_types liegt, wird die Aktion direkt ausgeführt.
        Andernfalls: Telegram-Nachricht mit ✅/❌ Buttons.
        """
        from src.services.database import Proposal

        # Auto-Approve prüfen
        auto_types = self._get_auto_approve_types(user_key)
        if proposal_type in auto_types and bot is not None:
            try:
                await self._execute(proposal_type, payload, user_key, str(chat_id), bot)
                confirm = self._format_auto_confirm(proposal_type, title, payload)
                app = self._apps.get(user_key)
                if app:
                    await app.bot.send_message(chat_id=chat_id, text=confirm, parse_mode="Markdown")
                logger.info(f"Auto-approved '{proposal_type}' für '{user_key}': {title}")
                return {"id": None, "title": title, "type": proposal_type, "auto_approved": True}
            except Exception as e:
                logger.error(f"Auto-Approve Ausführungsfehler: {e}")
                # Fallback: normaler Proposal-Flow

        payload_json = json.dumps(payload, default=str, ensure_ascii=False)
        icon = TYPE_ICONS.get(proposal_type, "📋")

        with self._db() as session:
            proposal = Proposal(
                proposal_type=proposal_type,
                title=title,
                description=description,
                payload_json=payload_json,
                user_key=user_key,
                created_by=created_by,
                status=STATUS_PENDING,
                telegram_chat_id=str(chat_id),
            )
            session.add(proposal)
            session.flush()
            proposal_id = proposal.id

        # Telegram-Nachricht senden
        msg_text = self._format_proposal_message(
            icon, title, description, proposal_type, payload
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Ausführen", callback_data=f"proposal_approve_{proposal_id}"),
                InlineKeyboardButton("❌ Ablehnen", callback_data=f"proposal_reject_{proposal_id}"),
            ]
        ])

        app = self._apps.get(user_key)
        if app:
            try:
                msg = await app.bot.send_message(
                    chat_id=chat_id,
                    text=msg_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                # message_id für späteres Editieren speichern
                with self._db() as session:
                    p = session.query(Proposal).filter_by(id=proposal_id).first()
                    if p:
                        p.telegram_message_id = str(msg.message_id)
            except Exception as e:
                logger.error(f"Proposal-Nachricht konnte nicht gesendet werden: {e}")

        logger.info(f"Proposal #{proposal_id} erstellt: {title} für '{user_key}' von '{created_by}'")
        return {"id": proposal_id, "title": title, "type": proposal_type}

    def _format_auto_confirm(self, proposal_type: str, title: str, payload: dict) -> str:
        """Bestätigungsnachricht für auto-approved Aktionen."""
        icon = TYPE_ICONS.get(proposal_type, "✅")
        lines = [f"{icon} *Direkt erledigt:* {title}"]
        if proposal_type == TYPE_REMINDER_CREATE:
            remind_at = payload.get("remind_at", "")
            if remind_at:
                try:
                    dt = datetime.fromisoformat(str(remind_at))
                    lines.append(f"⏰ {dt.strftime('%d.%m.%Y %H:%M Uhr')}")
                except Exception:
                    pass
        elif proposal_type == TYPE_TASK_CREATE:
            from src.services.task_service import PRIORITY_ICONS
            priority = payload.get("priority", "medium")
            lines.append(f"{PRIORITY_ICONS.get(priority, '')} Priorität: {priority}")
        return "\n".join(lines)

    def _format_proposal_message(
        self, icon: str, title: str, description: str, proposal_type: str, payload: dict
    ) -> str:
        """Baut den Nachrichtentext für einen Vorschlag."""
        lines = [f"{icon} *Vorschlag:* {title}"]

        if description:
            lines.append(f"\n_{description}_")

        # Typ-spezifische Details
        if proposal_type == TYPE_CALENDAR_CREATE:
            start = payload.get("start", "")
            if start:
                try:
                    dt = datetime.fromisoformat(str(start))
                    lines.append(f"\n🕐 {dt.strftime('%d.%m.%Y %H:%M Uhr')}")
                except Exception:
                    lines.append(f"\n🕐 {start}")

        elif proposal_type == TYPE_REMINDER_CREATE:
            remind_at = payload.get("remind_at", "")
            if remind_at:
                try:
                    dt = datetime.fromisoformat(str(remind_at))
                    lines.append(f"\n⏰ {dt.strftime('%d.%m.%Y %H:%M Uhr')}")
                except Exception:
                    lines.append(f"\n⏰ {remind_at}")

        elif proposal_type == TYPE_NOTE_CREATE:
            content = payload.get("content", "")
            if content:
                lines.append(f"\n📝 _{content[:100]}_")

        elif proposal_type == TYPE_TASK_CREATE:
            priority = payload.get("priority", "medium")
            from src.services.task_service import PRIORITY_ICONS
            p_icon = PRIORITY_ICONS.get(priority, "")
            lines.append(f"\n{p_icon} Priorität: {priority}")
            assigned_by = payload.get("assigned_by")
            if assigned_by:
                lines.append(f"_Zugewiesen von {assigned_by.capitalize()}_")

        lines.append("\n\nSoll ich das ausführen?")
        return "\n".join(lines)

    async def approve_proposal(self, proposal_id: int, bot) -> bool:
        """Genehmigt einen Vorschlag und führt die Aktion aus."""
        from src.services.database import Proposal

        with self._db() as session:
            proposal = session.query(Proposal).filter_by(
                id=proposal_id, status=STATUS_PENDING
            ).first()
            if not proposal:
                return False

            # Snapshot der Daten bevor Session schließt
            p_type = proposal.proposal_type
            p_payload = json.loads(proposal.payload_json)
            p_user_key = proposal.user_key
            p_chat_id = proposal.telegram_chat_id
            proposal.status = STATUS_APPROVED
            proposal.decided_at = datetime.utcnow()

        try:
            await self._execute(p_type, p_payload, p_user_key, p_chat_id, bot)
            logger.info(f"Proposal #{proposal_id} ausgeführt.")
            return True
        except Exception as e:
            logger.error(f"Proposal #{proposal_id} Ausführungsfehler: {e}")
            # Status zurücksetzen auf pending bei Fehler
            with self._db() as session:
                p = session.query(Proposal).filter_by(id=proposal_id).first()
                if p:
                    p.status = STATUS_PENDING
                    p.decided_at = None
            raise

    async def reject_proposal(self, proposal_id: int) -> bool:
        """Lehnt einen Vorschlag ab."""
        from src.services.database import Proposal

        with self._db() as session:
            proposal = session.query(Proposal).filter_by(
                id=proposal_id, status=STATUS_PENDING
            ).first()
            if not proposal:
                return False
            proposal.status = STATUS_REJECTED
            proposal.decided_at = datetime.utcnow()

        logger.info(f"Proposal #{proposal_id} abgelehnt.")
        return True

    async def get_open_proposals(self, user_key: str) -> list[dict]:
        """Gibt alle offenen Vorschläge für einen User zurück."""
        from src.services.database import Proposal

        with self._db() as session:
            proposals = (
                session.query(Proposal)
                .filter_by(user_key=user_key, status=STATUS_PENDING)
                .order_by(Proposal.created_at.desc())
                .limit(20)
                .all()
            )
            return [
                {
                    "id": p.id,
                    "type": p.proposal_type,
                    "title": p.title,
                    "created_by": p.created_by,
                    "created_at": p.created_at,
                }
                for p in proposals
            ]

    async def _execute(
        self, proposal_type: str, payload: dict, user_key: str, chat_id: str, bot
    ):
        """Führt die eigentliche Aktion basierend auf dem Proposal-Typ aus."""

        if proposal_type == TYPE_CALENDAR_CREATE:
            start = datetime.fromisoformat(str(payload["start"]))
            end = datetime.fromisoformat(str(payload["end"]))
            await bot.calendar_service.create_event(
                user_key=user_key,
                summary=payload["summary"],
                start=start,
                end=end,
                description=payload.get("description", ""),
            )

        elif proposal_type == TYPE_REMINDER_CREATE:
            remind_at = datetime.fromisoformat(str(payload["remind_at"]))
            await bot.reminder_service.create_reminder(
                user_key=user_key,
                user_chat_id=chat_id,
                content=payload["content"],
                remind_at=remind_at,
            )

        elif proposal_type == TYPE_NOTE_CREATE:
            await bot.notes_service.create_note(
                user_key=user_key,
                content=payload["content"],
                is_shared=payload.get("is_shared", False),
            )

        elif proposal_type == TYPE_TASK_CREATE:
            await bot.task_service.create_task(
                user_key=user_key,
                title=payload["title"],
                priority=payload.get("priority", "medium"),
                description=payload.get("description", ""),
                assigned_by=payload.get("assigned_by"),
            )

        elif proposal_type in (TYPE_AI_SUGGESTION, TYPE_SHARED_ACTION):
            # Freie Vorschläge: Nur bestätigen, keine weitere Aktion nötig
            pass

        else:
            raise ValueError(f"Unbekannter Proposal-Typ: {proposal_type}")
