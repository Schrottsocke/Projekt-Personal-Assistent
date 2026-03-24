"""
Freie Nachrichten Handler: KI versteht natürliche Sprache und
entscheidet, ob Kalender, Notiz, Erinnerung oder normaler Chat gemeint ist.
"""

import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes, Application

from src.services.rate_limiter import rate_limiter
from config.settings import settings

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

    # 3. Fokus-Modus prüfen
    try:
        from src.services.database import UserProfile, get_db
        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if profile and profile.focus_mode_until:
                tz = pytz.timezone(settings.TIMEZONE)
                now = datetime.now(tz)
                until = profile.focus_mode_until
                # tzinfo sicherstellen
                if until.tzinfo is None:
                    until = tz.localize(until)
                if now < until:
                    time_str = until.strftime("%H:%M")
                    await update.message.reply_text(
                        f"🎯 *Fokus-Modus aktiv bis {time_str}*\n\n"
                        "Ich halte deine Nachrichten zurück. Schreib `/fokus_ende` um den Fokus zu beenden.",
                        parse_mode="Markdown",
                    )
                    return
                else:
                    # Fokus abgelaufen – automatisch zurücksetzen
                    profile.focus_mode_until = None
    except Exception as e:
        logger.warning(f"Fokus-Modus-Check-Fehler: {e}")

    # Typing-Indikator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Spotify-Redirect-URL abfangen (User schickt Callback-URL nach OAuth)
        sp = getattr(bot, "spotify_service", None)
        if sp and sp.available and user_message.startswith("http") and "code=" in user_message:
            if sp.exchange_code(user_key, user_message.strip()):
                await update.message.reply_text(
                    "✅ *Spotify verbunden!* Du kannst jetzt Musik steuern.\n"
                    "Sag z.B. _\"Spiel Jazz\"_ oder _\"Pause\"_",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("❌ Spotify-Verbindung fehlgeschlagen. URL korrekt?")
            return

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

            # TTS: Wenn aktiviert → Antwort auch als Sprachnachricht senden
            tts_svc = getattr(bot, "tts_service", None)
            if tts_svc and tts_svc.available:
                try:
                    from src.services.database import UserProfile, get_db
                    with get_db()() as session:
                        profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                        if profile and profile.tts_enabled:
                            await tts_svc.send_voice(bot.app, chat_id, response)
                except Exception as tts_err:
                    logger.warning(f"TTS-Send-Fehler: {tts_err}")

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


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analysiert Fotos und Bilder via Vision-Modell."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    chat_id = update.effective_chat.id

    allowed, _ = rate_limiter.check(user_key)
    if not allowed:
        await update.message.reply_text("⏳ Rate-Limit erreicht – bitte kurz warten.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        # Größtes verfügbares Foto herunterladen
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()

        # Begleittext als Prompt (falls vorhanden)
        caption = update.message.caption or ""

        analysis = await bot.ai_service.analyze_image(
            image_bytes=bytes(image_bytes),
            user_prompt=caption,
            user_key=user_key,
        )

        if not analysis:
            await update.message.reply_text(
                "🖼️ Ich kann Bilder leider gerade nicht analysieren. "
                "Versuche es später nochmal."
            )
            return

        await update.message.reply_text(f"🖼️ {analysis}", parse_mode="Markdown")

        # Analyse auch als Nachricht durch Intent-Erkennung laufen lassen
        # damit z.B. "Rechnung → Aufgabe" oder "Termin → Kalender" erkannt wird
        if len(analysis) > 50:
            follow_up = await bot.ai_service.process_message(
                message=f"[Bildanalyse] {analysis}",
                user_key=user_key,
                chat_id=chat_id,
                bot=bot,
            )
            if follow_up:
                await update.message.reply_text(follow_up, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Foto-Handler-Fehler für {bot.name}: {e}", exc_info=True)
        await update.message.reply_text("❌ Bild konnte nicht verarbeitet werden.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Dokumente: Bilder als Dateien → Vision, andere → Hinweis."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    chat_id = update.effective_chat.id
    doc = update.message.document

    IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}

    if doc.mime_type in IMAGE_MIMETYPES:
        allowed, _ = rate_limiter.check(user_key)
        if not allowed:
            await update.message.reply_text("⏳ Rate-Limit erreicht – bitte kurz warten.")
            return

        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            doc_file = await doc.get_file()
            image_bytes = await doc_file.download_as_bytearray()
            caption = update.message.caption or ""

            analysis = await bot.ai_service.analyze_image(
                image_bytes=bytes(image_bytes),
                user_prompt=caption,
                user_key=user_key,
            )

            if analysis:
                await update.message.reply_text(f"🖼️ {analysis}", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Bild konnte nicht analysiert werden.")
        except Exception as e:
            logger.error(f"Dokument-Bild-Fehler für {bot.name}: {e}", exc_info=True)
            await update.message.reply_text("❌ Dokument konnte nicht verarbeitet werden.")
    else:
        # Andere Dateitypen: Hinweis geben
        filename = doc.file_name or "Datei"
        await update.message.reply_text(
            f"📎 *{filename}* erhalten.\n\n"
            "Ich kann aktuell nur Bilder analysieren (JPG, PNG, WEBP).\n"
            "PDFs und andere Dokumente folgen in einem späteren Update.",
            parse_mode="Markdown",
        )


def register_message_handlers(app: Application):
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
