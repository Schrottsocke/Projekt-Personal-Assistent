"""
Freie Nachrichten Handler: KI versteht natürliche Sprache und
entscheidet, ob Kalender, Notiz, Erinnerung oder normaler Chat gemeint ist.
"""

import logging
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes, Application

logger = logging.getLogger(__name__)


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_message = update.message.text
    user_key = bot.name.lower()
    chat_id = update.effective_chat.id

    # Typing-Indikator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Intent-Erkennung + Antwort generieren
        response = await bot.ai_service.process_message(
            message=user_message,
            user_key=user_key,
            chat_id=chat_id,
            bot=bot,
        )
        # Leere Antwort = Proposal wurde bereits als eigene Nachricht gesendet
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Message-Handler-Fehler für {bot.name}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Etwas ist schiefgelaufen. Versuche es nochmal oder nutze die Befehle (/hilfe)."
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Platzhalter für Sprachnachrichten (Phase 2)."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return
    await update.message.reply_text(
        "🎤 Sprachnachrichten werden in einer späteren Version unterstützt.\n"
        "Bitte schreib mir deine Nachricht als Text."
    )


def register_message_handlers(app: Application):
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
