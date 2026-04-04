"""
Shift Callback Handler: Verarbeitet InlineKeyboard-Antworten fuer Dienst-Rueckmeldungen.

Callback-Data-Format: shift_confirm:{entry_id}:{action}
Actions: ok, deviation, snooze, cancel
"""

import logging
import re
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    Application,
    filters,
)

logger = logging.getLogger(__name__)

CALLBACK_PATTERN = r"^shift_confirm:(\d+):(ok|deviation|snooze|cancel)$"

# ConversationHandler states fuer Abweichungs-Erfassung
ASK_START, ASK_END, ASK_BREAK, ASK_NOTE = range(4)


def get_bot(context: ContextTypes.DEFAULT_TYPE):
    return context.application.bot_data.get("bot_instance")


def _get_tracking_service():
    from src.services.shift_tracking_service import ShiftTrackingService
    svc = ShiftTrackingService()
    # Synchron initialisieren (init_db ist idempotent)
    from src.services.database import init_db, get_db
    init_db()
    svc._db = get_db()
    return svc


async def handle_shift_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Shift-Confirm InlineKeyboard Callbacks."""
    bot = get_bot(context)
    query = update.callback_query

    if not bot._is_authorized(update.effective_user.id):
        await query.answer("Keine Berechtigung.", show_alert=True)
        return

    await query.answer()

    match = re.match(CALLBACK_PATTERN, query.data)
    if not match:
        return

    entry_id = int(match.group(1))
    action = match.group(2)
    user_key = bot.name.lower()

    svc = _get_tracking_service()

    try:
        if action == "ok":
            result = svc.confirm_shift(entry_id, user_key, source="bot")
            shift_name = result.get("shift_type_name", "Dienst")
            await query.edit_message_text(
                f"*Dienst best\u00e4tigt*\n\n"
                f"{shift_name} am {result.get('date', '')} wurde als normal beendet markiert.",
                parse_mode="Markdown",
            )

        elif action == "cancel":
            result = svc.cancel_shift(entry_id, user_key, source="bot")
            shift_name = result.get("shift_type_name", "Dienst")
            await query.edit_message_text(
                f"*Dienst ausgefallen*\n\n"
                f"{shift_name} am {result.get('date', '')} wurde als ausgefallen markiert.",
                parse_mode="Markdown",
            )

        elif action == "snooze":
            result = svc.snooze_reminder(entry_id, user_key, minutes=60)
            await query.edit_message_text(
                "*Später erinnern*\n\n"
                "Ich erinnere dich in 60 Minuten nochmal.",
                parse_mode="Markdown",
            )

        elif action == "deviation":
            # Starte Conversation-Flow fuer Abweichungs-Erfassung
            context.user_data["shift_deviation_entry_id"] = entry_id
            context.user_data["shift_deviation_data"] = {}
            await query.edit_message_text(
                "*Abweichung erfassen*\n\n"
                "Wann hast du angefangen? _(Format: HH:MM)_",
                parse_mode="Markdown",
            )
            return ASK_START

    except ValueError as e:
        await query.edit_message_text(f"Fehler: {e}")
    except Exception as e:
        logger.error(f"Shift-Callback-Fehler: {e}")
        await query.edit_message_text("Fehler bei der Verarbeitung.")


async def ask_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Empfaengt tatsaechliche Startzeit, fragt nach Endzeit."""
    text = update.message.text.strip()
    if not re.match(r"^\d{2}:\d{2}$", text):
        await update.message.reply_text("Bitte im Format HH:MM eingeben (z.B. 06:30):")
        return ASK_START

    context.user_data["shift_deviation_data"]["actual_start"] = text
    await update.message.reply_text(
        "Wann hast du aufgeh\u00f6rt? _(Format: HH:MM)_",
        parse_mode="Markdown",
    )
    return ASK_END


async def ask_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Empfaengt tatsaechliche Endzeit, fragt nach Pause."""
    text = update.message.text.strip()
    if not re.match(r"^\d{2}:\d{2}$", text):
        await update.message.reply_text("Bitte im Format HH:MM eingeben (z.B. 14:30):")
        return ASK_END

    context.user_data["shift_deviation_data"]["actual_end"] = text
    await update.message.reply_text(
        "Pause in Minuten? _(0 wenn keine, oder Zahl eingeben)_",
        parse_mode="Markdown",
    )
    return ASK_BREAK


async def ask_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Empfaengt Pause, fragt nach Notiz."""
    text = update.message.text.strip()
    try:
        minutes = int(text)
        if minutes < 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Bitte eine Zahl eingeben (z.B. 30):")
        return ASK_BREAK

    context.user_data["shift_deviation_data"]["actual_break"] = minutes
    await update.message.reply_text(
        "Grund f\u00fcr die Abweichung? _(optional, 'skip' zum \u00dcberspringen)_",
        parse_mode="Markdown",
    )
    return ASK_NOTE


async def finish_deviation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Empfaengt optionale Notiz und speichert die Abweichung."""
    bot = get_bot(context)
    text = update.message.text.strip()
    note = text if text.lower() != "skip" else None

    entry_id = context.user_data.get("shift_deviation_entry_id")
    data = context.user_data.get("shift_deviation_data", {})
    user_key = bot.name.lower()

    svc = _get_tracking_service()

    try:
        result = svc.record_deviation(
            entry_id=entry_id,
            user_key=user_key,
            actual_start=data.get("actual_start", ""),
            actual_end=data.get("actual_end", ""),
            actual_break=data.get("actual_break", 0),
            note=note,
            source="bot",
        )
        shift_name = result.get("shift_type_name", "Dienst")
        delta = result.get("delta_minutes")
        delta_str = f"{delta:+d} Min" if delta is not None else ""

        await update.message.reply_text(
            f"*Abweichung gespeichert*\n\n"
            f"{shift_name} am {result.get('date', '')}\n"
            f"Ist: {data.get('actual_start')} \u2013 {data.get('actual_end')}\n"
            f"Pause: {data.get('actual_break', 0)} Min\n"
            f"Abweichung: {delta_str}\n"
            f"{f'Notiz: {note}' if note else ''}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Shift-Deviation-Fehler: {e}")
        await update.message.reply_text(f"Fehler: {e}")

    # Cleanup
    context.user_data.pop("shift_deviation_entry_id", None)
    context.user_data.pop("shift_deviation_data", None)
    return ConversationHandler.END


async def cancel_deviation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bricht den Abweichungs-Flow ab."""
    context.user_data.pop("shift_deviation_entry_id", None)
    context.user_data.pop("shift_deviation_data", None)
    await update.message.reply_text("Abweichungs-Erfassung abgebrochen.")
    return ConversationHandler.END


def register_shift_handlers(app: Application):
    """Registriert alle Shift-Tracking Handler."""
    # CallbackQueryHandler fuer die InlineKeyboard-Buttons
    app.add_handler(CallbackQueryHandler(handle_shift_callback, pattern=CALLBACK_PATTERN))

    # ConversationHandler fuer den Abweichungs-Flow (wird durch Callback gestartet)
    deviation_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_shift_callback, pattern=r"^shift_confirm:\d+:deviation$")],
        states={
            ASK_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_end)],
            ASK_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_break)],
            ASK_BREAK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_note)],
            ASK_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_deviation)],
        },
        fallbacks=[CommandHandler("cancel", cancel_deviation)],
        per_message=False,
    )
    app.add_handler(deviation_conv)
