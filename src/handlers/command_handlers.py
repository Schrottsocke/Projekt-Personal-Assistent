"""Telegram Command Handler (/kalender, /notiz, /erinnerung, etc.)"""

import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, Application

from config.settings import settings

logger = logging.getLogger(__name__)


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


async def cmd_hilfe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    text = (
        "🤖 *Dein persönlicher Assistent*\n\n"
        "*Befehle:*\n"
        "/kalender – Heutige & kommende Termine\n"
        "/neu\\_termin – Neuen Termin anlegen\n"
        "/notiz – Neue Notiz speichern\n"
        "/notizen – Alle Notizen anzeigen\n"
        "/erinnerung – Neue Erinnerung setzen\n"
        "/erinnerungen – Aktive Erinnerungen\n"
        "/briefing – Morgen-Briefing jetzt\n"
        "/gedaechtnis – Was ich über dich weiß\n"
        "/hilfe – Diese Hilfe\n\n"
        "💬 Oder schreib einfach frei – ich verstehe natürliche Sprache!\n"
        "_z.B. \"Erinnere mich morgen um 10 an Zahnarzt\"_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_kalender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    await update.message.reply_text("📅 Lade Kalender...")

    try:
        events = await bot.calendar_service.get_upcoming_events(
            user_key=bot.name.lower(), days=7
        )
        if not events:
            await update.message.reply_text(
                "📅 Keine Termine in den nächsten 7 Tagen."
            )
            return

        tz = pytz.timezone(settings.TIMEZONE)
        lines = ["📅 *Deine nächsten Termine:*\n"]
        for event in events:
            start = event.get("start", {})
            dt_str = start.get("dateTime", start.get("date", ""))
            summary = event.get("summary", "(kein Titel)")

            if "T" in dt_str:
                dt = datetime.fromisoformat(dt_str).astimezone(tz)
                date_fmt = dt.strftime("%a, %d.%m. um %H:%M Uhr")
            else:
                dt = datetime.fromisoformat(dt_str)
                date_fmt = dt.strftime("%a, %d.%m. (ganztägig)")

            lines.append(f"• {date_fmt}\n  *{summary}*")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Kalender-Fehler: {e}")
        await update.message.reply_text(
            "❌ Kalender konnte nicht geladen werden. "
            "Ist Google Calendar verbunden? (/start für Setup)"
        )


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    await update.message.reply_text("☕ Erstelle dein Briefing...")

    try:
        from src.scheduler.briefing import generate_briefing
        text = await generate_briefing(bot)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Briefing-Fehler: {e}")
        await update.message.reply_text("❌ Briefing konnte nicht erstellt werden.")


async def cmd_notiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📝 *Notiz speichern:*\nSchreib einfach:\n`/notiz Hier dein Text`\n\n"
            "Oder schreib mir frei: _\"Notiz: Milch kaufen\"_",
            parse_mode="Markdown"
        )
        return

    content = " ".join(args)
    try:
        note = await bot.notes_service.create_note(
            user_key=bot.name.lower(),
            content=content,
            is_shared=False
        )
        await update.message.reply_text(
            f"✅ Notiz gespeichert!\n📝 _{content}_", parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Notiz-Fehler: {e}")
        await update.message.reply_text("❌ Notiz konnte nicht gespeichert werden.")


async def cmd_notizen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    try:
        notes = await bot.notes_service.get_notes(user_key=bot.name.lower())
        if not notes:
            await update.message.reply_text("📝 Keine Notizen vorhanden.")
            return

        lines = ["📝 *Deine Notizen:*\n"]
        for i, note in enumerate(notes[-10:], 1):  # Letzte 10
            lines.append(f"{i}. {note['content']}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Notizen-Fehler: {e}")
        await update.message.reply_text("❌ Notizen konnten nicht geladen werden.")


async def cmd_erinnerung(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "⏰ *Erinnerung setzen:*\n\n"
            "Schreib mir frei:\n"
            "_\"Erinnere mich morgen um 9 Uhr an das Meeting\"_\n"
            "_\"In 2 Stunden: Wäsche aus der Maschine\"_\n\n"
            "Ich verstehe natürliche Zeitangaben!",
            parse_mode="Markdown"
        )
        return

    # Freier Text → KI parst Datum/Uhrzeit
    raw = " ".join(args)
    await update.message.reply_text(f"⏰ Verarbeite: _{raw}_...", parse_mode="Markdown")

    try:
        result = await bot.ai_service.parse_reminder(
            text=raw,
            user_key=bot.name.lower()
        )
        if result:
            reminder = await bot.reminder_service.create_reminder(
                user_key=bot.name.lower(),
                user_chat_id=update.effective_chat.id,
                content=result["content"],
                remind_at=result["remind_at"],
            )
            time_str = result["remind_at"].strftime("%d.%m.%Y um %H:%M Uhr")
            await update.message.reply_text(
                f"✅ Erinnerung gesetzt!\n⏰ {time_str}\n📌 _{result['content']}_",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❓ Konnte Datum/Uhrzeit nicht erkennen. "
                "Beispiel: _\"Morgen um 10 Uhr: Zahnarzt\"_",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Erinnerungs-Fehler: {e}")
        await update.message.reply_text("❌ Erinnerung konnte nicht gesetzt werden.")


async def cmd_erinnerungen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    try:
        reminders = await bot.reminder_service.get_active_reminders(
            user_key=bot.name.lower()
        )
        if not reminders:
            await update.message.reply_text("⏰ Keine aktiven Erinnerungen.")
            return

        tz = pytz.timezone(settings.TIMEZONE)
        lines = ["⏰ *Aktive Erinnerungen:*\n"]
        for r in reminders:
            dt = r["remind_at"].astimezone(tz)
            lines.append(f"• {dt.strftime('%d.%m. %H:%M')} – {r['content']}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erinnerungen-Fehler: {e}")
        await update.message.reply_text("❌ Erinnerungen konnten nicht geladen werden.")


async def cmd_gedaechtnis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    try:
        memories = await bot.memory_service.get_all_memories(user_key=bot.name.lower())
        if not memories:
            await update.message.reply_text(
                "🧠 Ich habe noch nichts Wichtiges über dich gespeichert.\n"
                "Erzähl mir etwas über dich!"
            )
            return

        lines = [f"🧠 *Was ich über {bot.name} weiß:*\n"]
        for m in memories[:15]:
            lines.append(f"• {m['memory']}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Gedächtnis-Fehler: {e}")
        await update.message.reply_text("❌ Gedächtnis konnte nicht geladen werden.")


def register_command_handlers(app: Application):
    app.add_handler(CommandHandler("hilfe", cmd_hilfe))
    app.add_handler(CommandHandler("help", cmd_hilfe))
    app.add_handler(CommandHandler("kalender", cmd_kalender))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("notiz", cmd_notiz))
    app.add_handler(CommandHandler("notizen", cmd_notizen))
    app.add_handler(CommandHandler("erinnerung", cmd_erinnerung))
    app.add_handler(CommandHandler("erinnerungen", cmd_erinnerungen))
    app.add_handler(CommandHandler("gedaechtnis", cmd_gedaechtnis))
    app.add_handler(CommandHandler("neu_termin", cmd_neu_termin))


async def cmd_neu_termin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📅 *Termin erstellen:*\n\n"
            "Schreib mir:\n"
            "_\"Zahnarzt am 15. März um 10 Uhr\"_\n"
            "_\"Meeting nächsten Montag 14:00-15:00\"_\n\n"
            "Ich erstelle den Termin automatisch in Google Calendar.",
            parse_mode="Markdown"
        )
        return

    raw = " ".join(args)
    await update.message.reply_text(f"📅 Erstelle Termin: _{raw}_...", parse_mode="Markdown")

    try:
        result = await bot.ai_service.parse_calendar_event(
            text=raw,
            user_key=bot.name.lower()
        )
        if result:
            event = await bot.calendar_service.create_event(
                user_key=bot.name.lower(),
                summary=result["summary"],
                start=result["start"],
                end=result["end"],
                description=result.get("description", ""),
            )
            await update.message.reply_text(
                f"✅ Termin erstellt!\n📅 *{result['summary']}*\n"
                f"🕐 {result['start'].strftime('%d.%m.%Y %H:%M')}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❓ Konnte den Termin nicht erkennen. "
                "Beispiel: _\"Zahnarzt am 15.3. um 10 Uhr\"_",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Termin-Fehler: {e}")
        await update.message.reply_text("❌ Termin konnte nicht erstellt werden.")
