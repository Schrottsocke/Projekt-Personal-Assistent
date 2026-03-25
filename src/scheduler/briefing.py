"""
Morgen-Briefing Generator.
"""

import logging

logger = logging.getLogger(__name__)


async def generate_briefing(bot) -> str:
    """Generiert das Morgen-Briefing für einen Bot/User."""
    user_key = bot.name.lower()

    try:
        events = await bot.calendar_service.get_todays_events(user_key=user_key)
    except Exception:
        events = []

    try:
        reminders = await bot.reminder_service.get_todays_reminders(user_key=user_key)
    except Exception:
        reminders = []

    try:
        memories = await bot.memory_service.search_memories(
            user_key=user_key, query="Interessen Aufgaben Gewohnheiten", limit=3
        )
    except Exception:
        memories = []

    try:
        open_tasks = await bot.task_service.get_open_tasks(user_key=user_key)
    except Exception:
        open_tasks = []

    # Neue Kontexte: Einkaufsliste + ungelesene Mails
    shopping_count = 0
    try:
        if hasattr(bot, "shopping_service") and bot.shopping_service:
            items = await bot.shopping_service.get_items(user_key)
            shopping_count = len(items)
    except Exception:
        pass

    unread_emails = 0
    try:
        if hasattr(bot, "email_service") and bot.email_service and bot.email_service.is_connected(user_key):
            unread_emails = await bot.email_service.get_unread_count(user_key)
    except Exception:
        pass

    briefing = await bot.ai_service.generate_morning_briefing(
        user_key=user_key,
        name=bot.name,
        events=events,
        reminders=reminders,
        memories=memories,
        open_tasks=open_tasks,
    )

    # Einkaufsliste- und Email-Hinweis anhängen
    extras = []
    if shopping_count > 0:
        extras.append(f"🛒 *Einkaufsliste:* {shopping_count} offene Artikel (_/einkaufsliste_)")
    if unread_emails > 0:
        extras.append(f"📬 *E-Mail:* {unread_emails} ungelesene Nachrichten (_/email_)")

    if extras:
        briefing += "\n\n" + "\n".join(extras)

    return briefing
