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

    return await bot.ai_service.generate_morning_briefing(
        user_key=user_key,
        name=bot.name,
        events=events,
        reminders=reminders,
        memories=memories,
    )
