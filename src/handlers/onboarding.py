"""
Onboarding-Flow: Wird beim ersten /start ausgeführt.
Fragt nach Präferenzen und richtet Google Calendar ein.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    Application,
)

from config.settings import settings

logger = logging.getLogger(__name__)

# Zustände des Onboarding-Flows
WELCOME, ASK_STYLE, ASK_INTERESTS, ASK_SCHEDULE, ASK_CALENDAR, CALENDAR_SETUP, DONE = range(7)


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    if not await bot._check_auth(update):
        return

    # Prüfe ob Onboarding bereits abgeschlossen
    is_onboarded = await _is_onboarded(bot, bot.name.lower())

    if is_onboarded:
        await update.message.reply_text(
            f"👋 Hey {bot.name}! Ich bin wieder da.\n\nWas kann ich für dich tun? (/hilfe für alle Befehle)"
        )
        return ConversationHandler.END

    # Onboarding starten
    await update.message.reply_text(
        f"👋 Hey {bot.name}! Schön, dass du da bist.\n\n"
        f"Ich bin dein persönlicher KI-Assistent. Ich helfe dir mit:\n"
        f"📅 Kalender & Termine\n"
        f"📝 Notizen\n"
        f"⏰ Erinnerungen\n"
        f"🤖 Allem, was du mir sagst!\n\n"
        f"Lass mich kurz ein paar Dinge einrichten...\n"
        f"Wie soll ich dich am liebsten ansprechen? (Einfach antworten)"
    )
    return ASK_STYLE


async def ask_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _bot = get_bot(context)
    nickname = update.message.text.strip()
    context.user_data["nickname"] = nickname

    keyboard = [
        [
            InlineKeyboardButton("🤙 Locker & direkt", callback_data="style_casual"),
            InlineKeyboardButton("👔 Professionell", callback_data="style_formal"),
        ],
        [InlineKeyboardButton("⚖️ Situationsabhängig", callback_data="style_mixed")],
    ]
    await update.message.reply_text(
        f"Super, {nickname}! 👍\n\nWie soll ich generell mit dir kommunizieren?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_INTERESTS


async def ask_interests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    style_map = {
        "style_casual": "locker und direkt, duze mich",
        "style_formal": "professionell und höflich",
        "style_mixed": "situationsabhängig anpassen",
    }
    context.user_data["style"] = style_map.get(query.data, "locker")

    await query.edit_message_text(
        "Verstanden! ✅\n\n"
        "Was sind deine Hauptinteressen oder womit kann ich dir am meisten helfen?\n"
        "_(z.B. Arbeit, Sport, Kochen, Reisen, Familie... schreib einfach frei)_",
        parse_mode="Markdown",
    )
    return ASK_SCHEDULE


async def ask_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fragt nach Arbeitszeiten und Quiet Hours."""
    context.user_data["interests"] = update.message.text.strip()

    keyboard = [
        [
            InlineKeyboardButton("🌅 Morgens (6–14 Uhr)", callback_data="focus_morgen"),
            InlineKeyboardButton("☀️ Mittags (10–18 Uhr)", callback_data="focus_mittag"),
        ],
        [
            InlineKeyboardButton("🌆 Abends (14–22 Uhr)", callback_data="focus_abend"),
            InlineKeyboardButton("⏭ Überspringen", callback_data="focus_skip"),
        ],
    ]
    await update.message.reply_text(
        "Super! 🙌\n\n"
        "Wann bist du am produktivsten?\n"
        "_(Hilft mir beim Tagesplan und damit ich dich nicht zur falschen Zeit störe)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return ASK_CALENDAR


async def ask_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wird durch Callback von ask_schedule aufgerufen."""
    query = update.callback_query
    await query.answer()

    focus_map = {
        "focus_morgen": "morgen",
        "focus_mittag": "mittag",
        "focus_abend": "abend",
        "focus_skip": None,
    }
    context.user_data["focus_time"] = focus_map.get(query.data)

    keyboard = [
        [
            InlineKeyboardButton("✅ Ja, verbinden", callback_data="calendar_yes"),
            InlineKeyboardButton("⏭ Später", callback_data="calendar_skip"),
        ]
    ]
    await query.edit_message_text(
        "Notiert! 📝\n\n"
        "Möchtest du jetzt Google Calendar verbinden?\n"
        "_(Damit kann ich Termine erstellen, anzeigen und dich daran erinnern)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return CALENDAR_SETUP


async def calendar_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    query = update.callback_query
    await query.answer()

    if query.data == "calendar_yes":
        try:
            auth_url = await bot.calendar_service.get_auth_url(user_key=bot.name.lower())
            await query.edit_message_text(
                f"📅 *Google Calendar verbinden:*\n\n"
                f"1. Öffne diesen Link:\n{auth_url}\n\n"
                f"2. Melde dich an und erlaube den Zugriff\n"
                f"3. Kopiere den Code und schick ihn mir hier\n\n"
                f"_(Der Code sieht aus wie: `4/0AX4XfWi...`)_",
                parse_mode="Markdown",
            )
            return DONE  # Wartet auf Auth-Code
        except Exception as e:
            logger.error(f"Calendar-Auth-Fehler: {e}")
            await query.edit_message_text(
                "❌ Google Calendar konnte nicht gestartet werden.\nDu kannst es später mit /kalender erneut versuchen."
            )
            await _finish_onboarding(bot, update.effective_chat.id, context)
            return ConversationHandler.END
    else:
        await query.edit_message_text("⏭ Kein Problem! Du kannst Google Calendar jederzeit über /kalender verbinden.")

    await _finish_onboarding(bot, update.effective_chat.id, context)
    return ConversationHandler.END


async def handle_calendar_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = get_bot(context)
    code = update.message.text.strip()

    await update.message.reply_text("🔄 Verbinde Google Calendar...")

    try:
        success = await bot.calendar_service.exchange_code(user_key=bot.name.lower(), code=code)
        if success:
            await update.message.reply_text(
                "✅ *Google Calendar erfolgreich verbunden!*\nIch kann jetzt deine Termine sehen und erstellen.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Code ungültig. Versuche es mit /neu_termin erneut.")
    except Exception as e:
        logger.error(f"Calendar-Code-Fehler: {e}")
        await update.message.reply_text("❌ Verbindung fehlgeschlagen. Versuche es später erneut.")

    await _finish_onboarding(bot, update.effective_chat.id, context)
    return ConversationHandler.END


async def _finish_onboarding(bot, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Speichert Onboarding-Daten und zeigt Abschluss-Nachricht."""
    user_key = bot.name.lower()
    nickname = context.user_data.get("nickname", bot.name)
    style = context.user_data.get("style", "locker")
    interests = context.user_data.get("interests", "")
    focus_time = context.user_data.get("focus_time")

    # Im Gedächtnis speichern + Chat-ID für proaktive Nachrichten
    try:
        memory_text = f"Der Nutzer heißt {nickname}. Kommunikationsstil: {style}. Interessen und Fokus: {interests}."
        if focus_time:
            memory_text += f" Ist am produktivsten am {focus_time}."
        await bot.memory_service.add_memory(user_key=user_key, content=memory_text)
        await bot.memory_service.mark_onboarded(user_key=user_key)

        # Chat-ID + Profil-Daten speichern
        from src.services.database import UserProfile, get_db

        with get_db()() as session:
            profile = session.query(UserProfile).filter_by(user_key=user_key).first()
            if profile:
                profile.chat_id = str(chat_id)
                profile.nickname = nickname
                profile.communication_style = style
                profile.interests = interests
                if focus_time:
                    profile.focus_time = focus_time
    except Exception as e:
        logger.error(f"Onboarding-Speicher-Fehler: {e}")

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎉 *Alles eingerichtet, {nickname}!*\n\n"
            f"Ich bin bereit. Schreib mir einfach was du brauchst, oder nutze:\n"
            f"/hilfe – Alle Befehle\n"
            f"/briefing – Dein tägliches Briefing\n\n"
            f"Jeden Morgen um {settings.MORNING_BRIEFING_TIME} Uhr schicke ich dir automatisch "
            f"eine Zusammenfassung deiner Termine und Aufgaben. 📅"
        ),
        parse_mode="Markdown",
    )


async def _is_onboarded(bot, user_key: str) -> bool:
    try:
        return await bot.memory_service.is_onboarded(user_key=user_key)
    except Exception:
        return False


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Einrichtung abgebrochen. Du kannst sie mit /start neu starten.")
    return ConversationHandler.END


def register_onboarding_handler(app: Application):
    handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ASK_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_style)],
            ASK_INTERESTS: [CallbackQueryHandler(ask_interests_callback, pattern="^style_")],
            ASK_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_schedule)],
            ASK_CALENDAR: [CallbackQueryHandler(ask_calendar, pattern="^focus_")],
            CALENDAR_SETUP: [CallbackQueryHandler(calendar_setup_callback, pattern="^calendar_")],
            DONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_calendar_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(handler)
