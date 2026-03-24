"""Telegram Command Handler (/kalender, /notiz, /erinnerung, etc.)"""

import logging
from datetime import datetime, timedelta
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
        "/tasks – Offene Aufgaben anzeigen\n"
        "/done <Nr> – Aufgabe abhaken\n"
        "/tabelle – Tabelle als Chat oder Excel-Datei\n"
        "/praesentation – PowerPoint-Präsentation erstellen\n"
        "/briefing – Morgen-Briefing jetzt\n"
        "/vorschlaege – Offene Vorschläge anzeigen\n"
        "/gedaechtnis – Was ich über dich weiß\n"
        "/autonomie – Einstellen was ich direkt ausführe\n"
        "/profil – Dein Persönlichkeitsprofil\n"
        "/fokus – Fokus-Modus aktivieren\n"
        "/fokus\\_ende – Fokus-Modus beenden\n"
        "/gemeinsam – Gemeinsamer Kalender mit Partner\n"
        "/tts – Sprachantworten an/aus\n"
        "/spotify – Spotify verbinden & steuern\n"
        "/smarthome – Smart Home Status & Steuerung\n"
        "/rezept – Rezept auf Chefkoch.de suchen\n"
        "/drive – Google Drive Dateien verwalten\n"
        "/hilfe – Diese Hilfe\n\n"
        "🎤 *Sprache:* Schick mir Sprachnachrichten – ich verstehe sie!\n\n"
        "🧠 *Ich lerne mit:*\n"
        "• Merke mir Fakten aus Gesprächen\n"
        "• Erkenne deine Stimmung und passe meinen Ton an\n"
        "• Schlage proaktiv Termine & Erinnerungen vor\n"
        "• Wenn du deinen Partner erwähnst, teile ich den Kontext\n"
        "• Kann dem Partner Aufgaben zuweisen\n"
        "• Sonntags bekommst du einen Wochenrückblick\n\n"
        "💬 Schreib oder sprich einfach frei!\n"
        "_z.B. \"Erinnere mich morgen um 10 an Zahnarzt\"_\n"
        "_z.B. \"Timer 25 Minuten\"_\n"
        "_z.B. \"Aufgabe: Steuer bis Freitag\"_\n"
        "_z.B. \"Erstelle eine Tabelle meiner Aufgaben\"_\n"
        "_z.B. \"Präsentation zu Remote Work\"_"
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
        top_facts = await bot.memory_service.get_top_facts(user_key=bot.name.lower(), limit=8)

        if not memories and not top_facts:
            await update.message.reply_text(
                "🧠 Ich habe noch nichts Wichtiges über dich gespeichert.\n"
                "Erzähl mir etwas über dich!"
            )
            return

        lines = [f"🧠 *Was ich über {bot.name} weiß:*\n"]

        # Bestätigte Fakten mit Konfidenz-Anzeige (Continuous Learning)
        high_conf = [f for f in top_facts if f["confirmation_count"] >= 2]
        if high_conf:
            lines.append("*✨ Bestätigte Fakten:*")
            for f in high_conf:
                stars = "⭐" * min(f["confirmation_count"], 5)
                lines.append(f"• {f['content']} _{stars}_")
            lines.append("")

        # Alle weiteren mem0-Memories
        if memories:
            lines.append("*📝 Weitere Erinnerungen:*")
            for m in memories[:10]:
                lines.append(f"• {m['memory']}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Gedächtnis-Fehler: {e}")
        await update.message.reply_text("❌ Gedächtnis konnte nicht geladen werden.")


async def cmd_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return
    try:
        tasks = await bot.task_service.get_open_tasks(user_key=bot.name.lower())
        text = bot.task_service.format_task_list(tasks)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Tasks-Fehler: {e}")
        await update.message.reply_text("❌ Aufgaben konnten nicht geladen werden.")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "✅ *Aufgabe abhaken:*\n`/done <Nummer>`\n\nz.B. `/done 3`\n\n"
            "Aufgaben siehst du mit /tasks",
            parse_mode="Markdown",
        )
        return

    try:
        task_id = int(args[0].strip("#"))
        task = await bot.task_service.complete_task(task_id=task_id, user_key=bot.name.lower())
        if task:
            await update.message.reply_text(
                f"✅ Erledigt: _{task['title']}_", parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❓ Aufgabe #{task_id} nicht gefunden. (/tasks)")
    except (ValueError, IndexError):
        await update.message.reply_text("❓ Bitte Aufgaben-Nummer angeben. Beispiel: `/done 3`")
    except Exception as e:
        logger.error(f"Done-Fehler: {e}")
        await update.message.reply_text("❌ Aufgabe konnte nicht abgehakt werden.")


async def cmd_autonomie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    user_key = bot.name.lower()

    try:
        from src.services.database import UserProfile, get_db
        from src.services.proposal_service import (
            TYPE_CALENDAR_CREATE, TYPE_REMINDER_CREATE, TYPE_NOTE_CREATE, TYPE_TASK_CREATE
        )

        all_types = {
            TYPE_CALENDAR_CREATE: "📅 Termine (calendar_create)",
            TYPE_REMINDER_CREATE: "⏰ Erinnerungen (reminder_create)",
            TYPE_NOTE_CREATE: "📝 Notizen (note_create)",
            TYPE_TASK_CREATE: "📋 Aufgaben (task_create)",
        }

        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if not profile:
                await update.message.reply_text("❌ Profil nicht gefunden. /start ausführen.")
                return

            current_raw = profile.auto_approve_types or "timer_create"
            current = set(t.strip() for t in current_raw.split(",") if t.strip())

            if not args:
                # Aktuelle Einstellungen anzeigen
                lines = ["⚡ *Autonomie-Einstellungen*\n"]
                lines.append("_Aktionen die ich direkt ausführe (ohne ✅-Button):_\n")
                lines.append("⏱ Timer (immer aktiv)\n")
                for t, label in all_types.items():
                    status = "✅ Aktiv" if t in current else "❌ Inaktiv"
                    lines.append(f"{status} – {label}")
                lines.append(
                    "\n*Umschalten:*\n"
                    "`/autonomie reminder_create` – Erinnerungen togglen\n"
                    "`/autonomie task_create` – Aufgaben togglen\n"
                    "`/autonomie note_create` – Notizen togglen\n"
                    "`/autonomie calendar_create` – Termine togglen"
                )
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
                return

            toggle_type = args[0].lower().strip()
            if toggle_type not in all_types:
                await update.message.reply_text(
                    f"❓ Unbekannter Typ: `{toggle_type}`\n"
                    "Gültige Werte: calendar_create, reminder_create, note_create, task_create",
                    parse_mode="Markdown",
                )
                return

            if toggle_type in current:
                current.discard(toggle_type)
                action_text = f"❌ Deaktiviert: {all_types[toggle_type]}\nIch frage ab jetzt wieder nach."
            else:
                current.add(toggle_type)
                action_text = f"✅ Aktiviert: {all_types[toggle_type]}\nIch führe das direkt aus."

            profile.auto_approve_types = ",".join(current)

        await update.message.reply_text(action_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Autonomie-Fehler: {e}")
        await update.message.reply_text("❌ Einstellungen konnten nicht gespeichert werden.")


async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    user_key = bot.name.lower()

    try:
        from src.services.database import UserProfile, get_db
        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if not profile:
                await update.message.reply_text("❌ Profil nicht gefunden. /start ausführen.")
                return

            if not args:
                # Profil anzeigen
                lines = [f"👤 *Profil: {profile.nickname or bot.name}*\n"]
                lines.append(f"💬 Stil: {profile.communication_style or 'nicht gesetzt'}")
                lines.append(f"🎯 Interessen: {profile.interests or 'nicht gesetzt'}")
                lines.append(f"🏢 Arbeitszeit: {profile.work_start or '?'} – {profile.work_end or '?'}")
                lines.append(f"🌙 Ruhezeit: ab {profile.quiet_start or 'nicht gesetzt'}")
                lines.append(f"🧠 Fokus: {profile.focus_time or 'nicht gesetzt'}")
                lines.append(f"📅 Wochenstruktur: {profile.week_structure or 'nicht gesetzt'}")
                lines.append(
                    "\n*Bearbeiten:*\n"
                    "`/profil arbeitszeit 09:00 18:00`\n"
                    "`/profil ruhezeit 22:00`\n"
                    "`/profil fokus morgen`  _(morgen/mittag/abend)_\n"
                    "`/profil woche Mo=Meetings, Fr=Planung`"
                )
                await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
                return

            # Profil bearbeiten
            field = args[0].lower()
            value = " ".join(args[1:])

            if field == "arbeitszeit" and len(args) >= 3:
                profile.work_start = args[1]
                profile.work_end = args[2]
                await update.message.reply_text(
                    f"✅ Arbeitszeit gesetzt: {args[1]} – {args[2]}"
                )
            elif field == "ruhezeit" and value:
                profile.quiet_start = value.split()[0]
                await update.message.reply_text(f"✅ Ruhezeit gesetzt: ab {profile.quiet_start}")
            elif field == "fokus" and value:
                valid_focus = {"morgen", "mittag", "abend"}
                if value.lower() in valid_focus:
                    profile.focus_time = value.lower()
                    await update.message.reply_text(f"✅ Fokuszeit gesetzt: {value.lower()}")
                else:
                    await update.message.reply_text("❓ Gültige Werte: morgen, mittag, abend")
            elif field == "woche" and value:
                profile.week_structure = value
                await update.message.reply_text(f"✅ Wochenstruktur gesetzt: {value}")
            else:
                await update.message.reply_text(
                    "❓ Unbekanntes Feld. Nutze `/profil` ohne Argumente für alle Optionen.",
                    parse_mode="Markdown",
                )

    except Exception as e:
        logger.error(f"Profil-Fehler: {e}")
        await update.message.reply_text("❌ Profil konnte nicht geladen werden.")


async def cmd_vorschlaege(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    try:
        proposals = await bot.proposal_service.get_open_proposals(user_key=bot.name.lower())
        if not proposals:
            await update.message.reply_text("📋 Keine offenen Vorschläge.")
            return

        lines = ["📋 *Offene Vorschläge:*\n"]
        for p in proposals:
            created = p["created_at"].strftime("%d.%m. %H:%M") if p.get("created_at") else ""
            lines.append(f"• #{p['id']} – {p['title']} _{created}_")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Vorschläge-Fehler: {e}")
        await update.message.reply_text("❌ Vorschläge konnten nicht geladen werden.")


async def cmd_tabelle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📊 *Tabelle erstellen:*\n\n"
            "Schreib mir, was du als Tabelle haben möchtest:\n"
            "`/tabelle meine offenen Aufgaben`\n"
            "`/tabelle Termine diese Woche`\n"
            "`/tabelle Ausgaben: Miete 800, Strom 120, Internet 40`\n\n"
            "Oder einfach frei: _\"Erstelle eine Tabelle meiner Aufgaben\"_",
            parse_mode="Markdown",
        )
        return

    description = " ".join(args)
    await update.message.reply_text("📊 Erstelle Tabelle...", parse_mode="Markdown")

    try:
        response = await bot.ai_service._handle_table_create(
            bot=bot,
            user_key=bot.name.lower(),
            message=description,
            chat_id=update.effective_chat.id,
        )
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Tabellen-Command-Fehler: {e}")
        await update.message.reply_text("❌ Tabelle konnte nicht erstellt werden.")


async def cmd_praesentation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📊 *Präsentation erstellen:*\n\n"
            "Nenne mir das Thema:\n"
            "`/praesentation Remote Work Best Practices`\n"
            "`/praesentation Meine Projektziele 2025`\n"
            "`/praesentation Einführung in Python`\n\n"
            "Oder einfach frei: _\"Erstelle eine Präsentation zu Thema X\"_",
            parse_mode="Markdown",
        )
        return

    topic = " ".join(args)
    await update.message.reply_text(
        f"📊 Erstelle Präsentation zu _{topic}_...", parse_mode="Markdown"
    )

    try:
        response = await bot.ai_service._handle_presentation_create(
            bot=bot,
            user_key=bot.name.lower(),
            message=topic,
            chat_id=update.effective_chat.id,
        )
        if response:
            await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Präsentation-Command-Fehler: {e}")
        await update.message.reply_text("❌ Präsentation konnte nicht erstellt werden.")


async def cmd_gemeinsam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt gemeinsame Kalender-Ansicht beider User + erkennt Konflikte."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    await update.message.reply_text("🔗 Lade gemeinsame Kalender...")

    user_key = bot.name.lower()
    partner_key = "nina" if user_key == "taake" else "taake"
    partner_name = partner_key.capitalize()

    try:
        my_events = await bot.calendar_service.get_upcoming_events(user_key=user_key, days=7)
    except Exception:
        my_events = []
    try:
        partner_events = await bot.calendar_service.get_upcoming_events(user_key=partner_key, days=7)
    except Exception:
        partner_events = []

    if not my_events and not partner_events:
        await update.message.reply_text("📅 Keine Termine in den nächsten 7 Tagen.")
        return

    tz = pytz.timezone(settings.TIMEZONE)

    def parse_event_dt(event: dict):
        start = event.get("start", {})
        dt_str = start.get("dateTime", start.get("date", ""))
        if not dt_str:
            return None
        try:
            if "T" in dt_str:
                return datetime.fromisoformat(dt_str).astimezone(tz)
            return tz.localize(datetime.fromisoformat(dt_str))
        except Exception:
            return None

    # Alle Events zusammenführen + sortieren
    all_events = []
    for e in my_events:
        dt = parse_event_dt(e)
        if dt:
            all_events.append(("me", dt, e))
    for e in partner_events:
        dt = parse_event_dt(e)
        if dt:
            all_events.append(("partner", dt, e))
    all_events.sort(key=lambda x: x[1])

    # Konflikte erkennen: Events im selben 1h-Fenster
    conflicts = []
    my_dts = [(parse_event_dt(e), e) for e in my_events if parse_event_dt(e)]
    partner_dts = [(parse_event_dt(e), e) for e in partner_events if parse_event_dt(e)]
    for m_dt, m_e in my_dts:
        for p_dt, p_e in partner_dts:
            diff = abs((m_dt - p_dt).total_seconds())
            if diff < 3600:  # innerhalb 1 Stunde
                conflicts.append((m_e, p_e, m_dt))

    lines = ["🔗 *Gemeinsamer Kalender (7 Tage)*\n"]

    if conflicts:
        lines.append("⚠️ *Terminüberschneidungen:*")
        for m_e, p_e, dt in conflicts[:3]:
            lines.append(
                f"• {dt.strftime('%a %d.%m. %H:%M')} – "
                f"_{m_e.get('summary', '?')}_ vs _{p_e.get('summary', '?')}_"
            )
        lines.append("")

    lines.append("*Alle Termine:*")
    for who, dt, event in all_events[:15]:
        icon = "👤" if who == "me" else f"👥 {partner_name}"
        lines.append(f"• {dt.strftime('%a %d.%m. %H:%M')} {icon} – {event.get('summary', '?')}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schaltet Text-to-Speech (Sprachantworten) an/aus."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    try:
        from src.services.database import UserProfile, get_db
        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if not profile:
                await update.message.reply_text("❌ Profil nicht gefunden.")
                return

            tts_svc = getattr(bot, "tts_service", None)
            if tts_svc and not tts_svc.available:
                await update.message.reply_text(
                    "🔇 TTS nicht verfügbar.\n`pip install gTTS` auf dem Server ausführen.",
                    parse_mode="Markdown",
                )
                return

            profile.tts_enabled = not bool(profile.tts_enabled)
            status = "aktiviert 🔊" if profile.tts_enabled else "deaktiviert 🔇"
            await update.message.reply_text(
                f"🎤 *Sprachantworten {status}*\n\n"
                f"{'Ich antworte jetzt auch als Sprachnachricht.' if profile.tts_enabled else 'Ich antworte nur noch als Text.'}",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"TTS-Toggle-Fehler: {e}")
        await update.message.reply_text("❌ Einstellung konnte nicht gespeichert werden.")


async def cmd_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Spotify-Verbindung und Steuerung."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    user_key = bot.name.lower()
    sp = getattr(bot, "spotify_service", None)

    if not sp or not sp.available:
        await update.message.reply_text(
            "🎵 *Spotify nicht konfiguriert.*\n\n"
            "Füge in `.env` hinzu:\n"
            "`SPOTIFY_CLIENT_ID=...`\n"
            "`SPOTIFY_CLIENT_SECRET=...`\n"
            "`SPOTIFY_REDIRECT_URI=http://localhost:8888/callback`\n\n"
            "App erstellen auf: developer.spotify.com/dashboard",
            parse_mode="Markdown",
        )
        return

    # Redirect-URL-Handling: User sendet die vollständige Callback-URL
    if args and args[0].startswith("http"):
        redirect_url = " ".join(args)
        if sp.exchange_code(user_key, redirect_url):
            await update.message.reply_text(
                "✅ *Spotify verbunden!*\n\n"
                "Du kannst jetzt sagen:\n"
                "• _Spiel entspannende Musik_\n"
                "• _Pause_\n"
                "• _Nächster Song_\n"
                "• _Lautstärke 70%_",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Verbindung fehlgeschlagen. URL korrekt?")
        return

    # Sub-commands
    if not args:
        if sp.is_connected(user_key):
            current = await sp.current(user_key)
            await update.message.reply_text(
                f"🎵 *Spotify verbunden*\n\n{current or 'Nichts aktiv.'}\n\n"
                "Steuerung per Text: _\"Spiel Jazz\"_, _\"Pause\"_, _\"Nächster Song\"_",
                parse_mode="Markdown",
            )
        else:
            url = sp.get_auth_url(user_key)
            await update.message.reply_text(
                f"🎵 *Spotify verbinden:*\n\n"
                f"1. Öffne: {url}\n"
                f"2. Melde dich an → Zugriff erlauben\n"
                f"3. Kopiere die vollständige Redirect-URL (z.B. `http://localhost:8888/callback?code=...`)\n"
                f"4. Sende sie mit: `/spotify <URL>`",
                parse_mode="Markdown",
            )
        return

    cmd = args[0].lower()
    if cmd == "pause":
        result = await sp.pause(user_key)
    elif cmd in ("skip", "next", "weiter"):
        result = await sp.skip(user_key)
    elif cmd == "play":
        query = " ".join(args[1:])
        result = await sp.play(user_key, query)
    else:
        result = f"❓ Unbekannt: `{cmd}`. Nutze: play, pause, skip"
    await update.message.reply_text(result or "❌ Spotify-Fehler", parse_mode="Markdown")


async def cmd_smarthome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smart Home Status und direkte Steuerung via HA."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    ha = getattr(bot, "smarthome_service", None)
    args = context.args

    if args:
        # Direktbefehl: /smarthome Licht Wohnzimmer aus
        command = " ".join(args)
        result = await ha.execute_command(command) if ha else "❌ Smart Home nicht konfiguriert."
        await update.message.reply_text(result, parse_mode="Markdown")
    else:
        # Status-Übersicht
        result = await ha.get_status_summary() if ha else "❌ Smart Home nicht konfiguriert."
        await update.message.reply_text(result, parse_mode="Markdown")


async def cmd_fokus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktiviert den Fokus-Modus für eine bestimmte Dauer."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    user_key = bot.name.lower()
    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz)

    if not args:
        await update.message.reply_text(
            "🎯 *Fokus-Modus:*\n\n"
            "`/fokus 25` – 25 Minuten Fokus\n"
            "`/fokus 90` – 90 Minuten Fokus\n"
            "`/fokus 16:00` – Fokus bis 16:00 Uhr\n\n"
            "Während des Fokus-Modus halte ich Nachrichten zurück.\n"
            "Dringende Erinnerungen (mit 'dringend') kommen trotzdem durch.\n\n"
            "Beenden: `/fokus_ende`",
            parse_mode="Markdown",
        )
        return

    try:
        from src.services.database import UserProfile, get_db

        raw = args[0].strip()
        if ":" in raw:
            # Uhrzeit-Format: "16:00"
            h, m = (int(x) for x in raw.split(":"))
            until = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if until <= now:
                until += timedelta(days=1)
            label = until.strftime("%H:%M Uhr")
        else:
            # Minuten-Format: "90"
            minutes = int(raw)
            if minutes <= 0 or minutes > 480:
                await update.message.reply_text("❓ Bitte eine Dauer zwischen 1 und 480 Minuten angeben.")
                return
            until = now + timedelta(minutes=minutes)
            label = f"{until.strftime('%H:%M')} Uhr ({minutes} Min.)"

        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if not profile:
                await update.message.reply_text("❌ Profil nicht gefunden. /start ausführen.")
                return
            # Als UTC in DB speichern
            profile.focus_mode_until = until.astimezone(pytz.utc).replace(tzinfo=None)

        await update.message.reply_text(
            f"🎯 *Fokus-Modus aktiv bis {label}*\n\n"
            "Ich halte Nachrichten und proaktive Benachrichtigungen zurück.\n"
            "Viel Fokus! 💪\n\n"
            "Beenden: `/fokus_ende`",
            parse_mode="Markdown",
        )

    except (ValueError, IndexError):
        await update.message.reply_text(
            "❓ Format: `/fokus 90` (Minuten) oder `/fokus 16:00` (Uhrzeit)",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Fokus-Fehler: {e}")
        await update.message.reply_text("❌ Fokus-Modus konnte nicht gesetzt werden.")


async def cmd_fokus_ende(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Beendet den Fokus-Modus vorzeitig."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    user_key = bot.name.lower()
    try:
        from src.services.database import UserProfile, get_db
        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if profile and profile.focus_mode_until:
                profile.focus_mode_until = None
                await update.message.reply_text(
                    "✅ *Fokus-Modus beendet.*\n\n"
                    "Willkommen zurück! Was kann ich für dich tun?",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text("ℹ️ Kein aktiver Fokus-Modus.")
    except Exception as e:
        logger.error(f"Fokus-Ende-Fehler: {e}")
        await update.message.reply_text("❌ Fehler beim Beenden des Fokus-Modus.")


async def cmd_rezept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sucht ein Rezept auf Chefkoch.de."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "🍳 *Rezept suchen:*\n\n"
            "`/rezept Pasta Carbonara`\n"
            "`/rezept Schokoladenkuchen`\n"
            "`/rezept Was kann ich mit Brokkoli machen?`\n\n"
            "Oder einfach schreiben: _\"Zeig mir ein Rezept für Schnitzel\"_",
            parse_mode="Markdown",
        )
        return

    query = " ".join(args)
    await update.message.reply_text(f"🍳 Suche Rezepte für _{query}_...", parse_mode="Markdown")

    ck = getattr(bot, "chefkoch_service", None)
    if not ck:
        await update.message.reply_text("❌ Chefkoch-Service nicht verfügbar.")
        return

    try:
        result = await ck.search_and_format(query)
        await update.message.reply_text(result, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Rezept-Befehl-Fehler: {e}")
        await update.message.reply_text("❌ Rezeptsuche fehlgeschlagen. Bitte nochmal versuchen.")


async def cmd_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Google Drive Dateiverwaltung."""
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    args = context.args
    user_key = bot.name.lower()
    drive = getattr(bot, "drive_service", None)

    if not drive:
        await update.message.reply_text("❌ Drive-Service nicht verfügbar.")
        return

    # Auth-Code-Handling: /drive auth <code>
    if args and args[0].lower() == "auth" and len(args) > 1:
        code = " ".join(args[1:]).strip()
        success = await drive.exchange_code(user_key, code)
        if success:
            await update.message.reply_text(
                "✅ *Google Drive verbunden!*\n\n"
                "Du kannst jetzt:\n"
                "• `/drive` – Dateien anzeigen\n"
                "• `/drive suche <Begriff>` – Datei suchen\n"
                "• Generierte Tabellen/Präsentationen werden automatisch in Drive gespeichert",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Code ungültig oder abgelaufen. Bitte `/drive` erneut ausführen.")
        return

    # Nicht verbunden → OAuth-Flow starten
    if not drive.is_connected(user_key):
        try:
            url = await drive.get_auth_url(user_key)
            await update.message.reply_text(
                "☁️ *Google Drive verbinden:*\n\n"
                f"1. Öffne diesen Link:\n{url}\n\n"
                "2. Melde dich mit deinem Google-Konto an\n"
                "3. Kopiere den angezeigten Code\n"
                "4. Sende: `/drive auth <Code>`",
                parse_mode="Markdown",
            )
        except FileNotFoundError:
            await update.message.reply_text(
                "❌ Google Credentials nicht gefunden.\n"
                "Bitte `config/google_credentials.json` von der Google Cloud Console hochladen.",
            )
        return

    # Suche
    if args and args[0].lower() == "suche" and len(args) > 1:
        query = " ".join(args[1:])
        await update.message.reply_text(f"🔍 Suche in Drive: _{query}_...", parse_mode="Markdown")
        try:
            files = await drive.list_files(user_key=user_key, query=query, limit=10)
            await update.message.reply_text(drive.format_file_list(files), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Drive-Suche-Fehler: {e}")
            await update.message.reply_text("❌ Suche fehlgeschlagen.")
        return

    # Standardmäßig: letzte Dateien anzeigen
    await update.message.reply_text("☁️ Lade Drive-Dateien...")
    try:
        files = await drive.list_files(user_key=user_key, limit=10)
        await update.message.reply_text(drive.format_file_list(files), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Drive-List-Fehler: {e}")
        await update.message.reply_text("❌ Drive-Dateien konnten nicht geladen werden.")


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
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("autonomie", cmd_autonomie))
    app.add_handler(CommandHandler("profil", cmd_profil))
    app.add_handler(CommandHandler("vorschlaege", cmd_vorschlaege))
    app.add_handler(CommandHandler("tabelle", cmd_tabelle))
    app.add_handler(CommandHandler("praesentation", cmd_praesentation))
    app.add_handler(CommandHandler("fokus", cmd_fokus))
    app.add_handler(CommandHandler("fokus_ende", cmd_fokus_ende))
    app.add_handler(CommandHandler("gemeinsam", cmd_gemeinsam))
    app.add_handler(CommandHandler("tts", cmd_tts))
    app.add_handler(CommandHandler("spotify", cmd_spotify))
    app.add_handler(CommandHandler("smarthome", cmd_smarthome))
    app.add_handler(CommandHandler("rezept", cmd_rezept))
    app.add_handler(CommandHandler("drive", cmd_drive))


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
