"""
Proposal Handler: Verarbeitet Button-Klicks (✅/❌) und /vorschlaege Command.
"""

import logging
import re
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Application,
)

from config.settings import settings

logger = logging.getLogger(__name__)

CALLBACK_PATTERN = r"^proposal_(approve|reject)_(\d+)$"


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


async def handle_proposal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet ✅ Ausführen / ❌ Ablehnen Button-Klicks."""
    bot = get_bot(context)
    query = update.callback_query
    await query.answer()

    if not bot._is_authorized(update.effective_user.id):
        await query.answer("⛔ Keine Berechtigung.", show_alert=True)
        return

    match = re.match(CALLBACK_PATTERN, query.data)
    if not match:
        return

    action = match.group(1)
    proposal_id = int(match.group(2))

    if action == "approve":
        await _approve(query, proposal_id, bot)
    else:
        await _reject(query, proposal_id, bot)


async def _approve(query, proposal_id: int, bot):
    await query.edit_message_text(
        f"{query.message.text}\n\n⏳ _Wird ausgeführt..._",
        parse_mode="Markdown",
    )
    try:
        success = await bot.proposal_service.approve_proposal(proposal_id, bot)
        if success:
            await query.edit_message_text(
                f"{_strip_buttons_text(query.message.text)}\n\n✅ *Ausgeführt!*",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                f"{_strip_buttons_text(query.message.text)}\n\n"
                "⚠️ Vorschlag nicht gefunden oder bereits entschieden.",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Approve-Fehler für Proposal #{proposal_id}: {e}")
        await query.edit_message_text(
            f"{_strip_buttons_text(query.message.text)}\n\n"
            "❌ Ausführung fehlgeschlagen. Bitte prüfe die Einstellungen.",
            parse_mode="Markdown",
        )


async def _reject(query, proposal_id: int, bot):
    try:
        await bot.proposal_service.reject_proposal(proposal_id)
        await query.edit_message_text(
            f"{_strip_buttons_text(query.message.text)}\n\n❌ *Abgelehnt.*",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Reject-Fehler für Proposal #{proposal_id}: {e}")


def _strip_buttons_text(text: str) -> str:
    """Entfernt die 'Soll ich das ausführen?'-Zeile aus dem Text."""
    return text.replace("\n\nSoll ich das ausführen?", "").strip()


async def cmd_vorschlaege(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle offenen Vorschläge."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    proposals = await bot.proposal_service.get_open_proposals(user_key=bot.name.lower())

    if not proposals:
        await update.message.reply_text(
            "📋 Keine offenen Vorschläge.\n\n"
            "Vorschläge entstehen automatisch wenn du mich bittest,\n"
            "etwas zu erstellen – z.B. _\"Zahnarzt morgen um 10\"_.",
            parse_mode="Markdown",
        )
        return

    tz = pytz.timezone(settings.TIMEZONE)
    lines = [f"📋 *Offene Vorschläge ({len(proposals)}):*\n"]
    for p in proposals:
        dt = p["created_at"]
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt).astimezone(tz)
        icon = {"calendar_create": "📅", "reminder_create": "⏰",
                "note_create": "📝", "ai_suggestion": "🤖", "shared_action": "🔗"}.get(p["type"], "📋")
        lines.append(
            f"{icon} *{p['title']}*\n"
            f"   von: {p['created_by']} · {dt.strftime('%d.%m. %H:%M')}\n"
            f"   ID: #{p['id']}"
        )

    lines.append("\n_Scroll hoch um die Buttons zu finden, oder schreib erneut._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def register_proposal_handlers(app: Application):
    # CallbackQueryHandler muss VOR ConversationHandler registriert werden
    app.add_handler(CallbackQueryHandler(handle_proposal_callback, pattern=CALLBACK_PATTERN))
    app.add_handler(CommandHandler("vorschlaege", cmd_vorschlaege))
