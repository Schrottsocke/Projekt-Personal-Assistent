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
from src.utils.telegram import escape_md, split_message
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
            await update.message.reply_text("📊 Tages-Limit erreicht. Morgen bin ich wieder voll dabei!")
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
                    until = pytz.utc.localize(until).astimezone(tz)
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
                    '✅ *Spotify verbunden!* Du kannst jetzt Musik steuern.\nSag z.B. _"Spiel Jazz"_ oder _"Pause"_',
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
        # Leere Antwort: entweder Proposal wurde gesendet, oder AI hat nichts geliefert
        if response is None or (isinstance(response, str) and response.strip() == ""):
            response = "Ich konnte leider keine Antwort generieren. Versuche es bitte nochmal oder nutze /hilfe."
        for chunk in split_message(response):
            await update.message.reply_text(chunk, parse_mode="Markdown")

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
            f"🎤 _Verstanden: {escape_md(transcript)}_",
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
            for chunk in split_message(response):
                await update.message.reply_text(chunk, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Voice-Handler-Fehler für {bot.name}: {e}", exc_info=True)
        await update.message.reply_text("❌ Sprachnachricht konnte nicht verarbeitet werden. Versuche es als Text.")


# Keywords die den Dokument-Scan-Workflow auslösen (in Caption)
_SCAN_KEYWORDS = {
    "scan",
    "dokument",
    "brief",
    "rechnung",
    "vertrag",
    "arztbrief",
    "behörde",
    "ausweis",
    "beleg",
    "kontoauszug",
    "quittung",
}


def _is_scan_intent(caption: str) -> bool:
    """True wenn kein Caption (=default scan) oder Caption enthält Scan-Keyword."""
    if not caption:
        return True
    caption_lower = caption.lower()
    return any(kw in caption_lower for kw in _SCAN_KEYWORDS)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Analysiert Fotos:
    - Kein Caption / Scan-Keywords → Dokument-Scan-Workflow
    - Sonst → bestehende Vision-Analyse (unverändert)
    """
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

        caption = update.message.caption or ""

        # --- Dokument-Scan-Workflow ---
        if _is_scan_intent(caption):
            await update.message.reply_text("🔍 Analysiere Dokument...")
            from src.workflows.document_scan_workflow import run_document_scan

            result = await run_document_scan(bytes(image_bytes), user_key, chat_id, bot, caption)
            await update.message.reply_text(result, parse_mode="Markdown")
            return

        # --- Bestehender Vision-Analyse-Flow ---
        analysis = await bot.ai_service.analyze_image(
            image_bytes=bytes(image_bytes),
            user_prompt=caption,
            user_key=user_key,
        )

        if not analysis:
            await update.message.reply_text(
                "🖼️ Ich kann Bilder leider gerade nicht analysieren. Versuche es später nochmal."
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
    """
    Verarbeitet Dokument-Dateien:
    - Bilder (JPG/PNG/etc.) → Scan-Workflow oder Vision
    - PDFs → Scan-Workflow (Text-Extraktion via PyPDF2 + Analyse)
    - Andere → Hinweis
    """
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    chat_id = update.effective_chat.id
    doc = update.message.document

    IMAGE_MIMETYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
    }

    allowed, _ = rate_limiter.check(user_key)
    if not allowed:
        await update.message.reply_text("⏳ Rate-Limit erreicht – bitte kurz warten.")
        return

    caption = update.message.caption or ""

    if doc.mime_type in IMAGE_MIMETYPES:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        try:
            doc_file = await doc.get_file()
            image_bytes = await doc_file.download_as_bytearray()

            if _is_scan_intent(caption):
                await update.message.reply_text("🔍 Analysiere Dokument...")
                from src.workflows.document_scan_workflow import run_document_scan

                result = await run_document_scan(bytes(image_bytes), user_key, chat_id, bot, caption)
                await update.message.reply_text(result, parse_mode="Markdown")
            else:
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

    elif doc.mime_type == "application/pdf":
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await update.message.reply_text("🔍 Analysiere PDF-Dokument...")
        try:
            doc_file = await doc.get_file()
            pdf_bytes = await doc_file.download_as_bytearray()

            # PDF-Text via PyPDF2 extrahieren, dann Analyse
            text = _extract_pdf_text(bytes(pdf_bytes))
            from src.workflows.document_scan_workflow import (
                _analyze_document,
                _save_to_db,
                _format_response,
            )

            analysis = await _analyze_document(text, caption, bot.ai_service)

            doc_type_label = analysis.get("document_type", "Sonstiges")
            import datetime as dt

            today = dt.datetime.now().strftime("%Y-%m-%d")
            filename = f"{today}_{doc_type_label}.pdf"

            _save_to_db(
                user_key=user_key,
                doc_type=doc_type_label,
                filename=filename,
                drive_link=None,
                drive_file_id=None,
                summary=analysis.get("summary"),
                sender=analysis.get("sender"),
                amount=analysis.get("amount"),
            )

            actions = analysis.get("actions", [])
            _type_map = {
                "task": "task_create",
                "reminder": "reminder_create",
                "calendar": "calendar_create",
            }
            for action in actions:
                try:
                    await bot.proposal_service.create_proposal(
                        user_key=user_key,
                        proposal_type=_type_map.get(action.get("type", ""), "task_create"),
                        title=action.get("title", "Aktion"),
                        description=action.get("context", ""),
                        payload=action,
                        created_by="document_scan",
                        chat_id=str(chat_id),
                        bot=bot,
                    )
                except Exception as pe:
                    logger.error(f"PDF-Proposal-Fehler: {pe}")

            result = _format_response(
                doc_type_label=doc_type_label,
                sender=analysis.get("sender"),
                summary=analysis.get("summary", "Analyse abgeschlossen."),
                amount=analysis.get("amount"),
                filename=filename,
                drive_link=None,
                pdf_path=None,
                proposals_created=len(actions),
                ocr_method="text",
                ocr_confidence=100.0,
                text_length=len(text),
            )
            await update.message.reply_text(result, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"PDF-Handler-Fehler für {bot.name}: {e}", exc_info=True)
            await update.message.reply_text("❌ PDF konnte nicht verarbeitet werden.")
    else:
        filename = doc.file_name or "Datei"
        await update.message.reply_text(
            f"📎 *{filename}* erhalten.\n\n"
            "Ich kann Bilder (JPG, PNG, WEBP) und PDFs analysieren.\n"
            "Andere Dateitypen werden noch nicht unterstützt.",
            parse_mode="Markdown",
        )


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrahiert Text aus PDF-Bytes via PyPDF2."""
    try:
        import io
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages[:10]:  # Max 10 Seiten
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception as e:
        logger.warning(f"PDF-Text-Extraktion fehlgeschlagen: {e}")
        return ""


def register_message_handlers(app: Application):
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
