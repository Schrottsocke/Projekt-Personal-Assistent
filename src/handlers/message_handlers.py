"""
Freie Nachrichten Handler: KI versteht natürliche Sprache und
entscheidet, ob Kalender, Notiz, Erinnerung oder normaler Chat gemeint ist.
"""

import logging
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes, Application

from src.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# Maximale Nachrichtenlänge in Zeichen.
# Längere Nachrichten werden abgeschnitten und der User informiert.
# Begründung: Ein 10.000-Zeichen-Text würde ~7.500 Tokens kosten –
# bei jedem API-Call. Die Grenze schützt vor versehentlichem
# oder absichtlichem Credit-Drain durch sehr lange Eingaben.
MAX_MESSAGE_LENGTH = 2000


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    chat_id = update.effective_chat.id

    # 1. Rate Limiting prüfen
    allowed, reason = rate_limiter.check(user_key)
    if not allowed:
        if reason == "minute":
            await update.message.reply_text(
                "⏳ Kurz durchatmen – so viele Nachrichten auf einmal kann ich nicht verarbeiten.\n"
                "Warte eine Minute und schreib dann nochmal."
            )
        else:
            await update.message.reply_text(
                "📊 Tages-Limit erreicht. Morgen bin ich wieder voll dabei!"
            )
        return

    # 2. Eingabelänge prüfen und ggf. kürzen
    user_message = update.message.text
    if len(user_message) > MAX_MESSAGE_LENGTH:
        user_message = user_message[:MAX_MESSAGE_LENGTH]
        await update.message.reply_text(
            f"✂️ _Deine Nachricht war sehr lang und wurde auf {MAX_MESSAGE_LENGTH} Zeichen gekürzt._",
            parse_mode="Markdown",
        )

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
    """Verarbeitet Sprachnachrichten via Groq Whisper."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    chat_id = update.effective_chat.id

    allowed, reason = rate_limiter.check(user_key)
    if not allowed:
        await update.message.reply_text("⏳ Rate-Limit erreicht – bitte kurz warten.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Audiodatei von Telegram herunterladen
        voice_file = await update.message.voice.get_file()
        audio_bytes = await voice_file.download_as_bytearray()

        transcript = await bot.ai_service.transcribe_voice(bytes(audio_bytes))

        if not transcript:
            await update.message.reply_text(
                "🎤 Sprachnachrichten werden leider noch nicht unterstützt.\n"
                "Kein GROQ_API_KEY konfiguriert – bitte als Text schreiben."
            )
            return

        # Transkript anzeigen, dann normal verarbeiten
        await update.message.reply_text(
            f"🎤 _Verstanden: {transcript}_",
            parse_mode="Markdown",
        )

        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        response = await bot.ai_service.process_message(
            message=transcript,
            user_key=user_key,
            chat_id=chat_id,
            bot=bot,
        )
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Voice-Handler-Fehler für {bot.name}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sprachnachricht konnte nicht verarbeitet werden. Versuche es als Text."
        )


def register_message_handlers(app: Application):
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
