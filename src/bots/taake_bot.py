"""Taakes persönlicher Assistent-Bot."""

from config.settings import settings
from src.bots.base_bot import BaseAssistantBot


class TaakeBot(BaseAssistantBot):
    def __init__(self):
        config = settings.get_bot_configs()["taake"]
        super().__init__(config)

    def get_system_prompt(self) -> str:
        return (
            "Du bist Taakes persönlicher KI-Assistent. "
            "Du kennst Taake gut und hilfst ihm mit Kalender, Notizen, Erinnerungen und allem anderen. "
            "Du bist direkt, locker und effizient. Kein unnötiges Blabla. "
            "Wenn du etwas Wichtiges über Taake lernst, merkst du dir das. "
            "Antworte auf Deutsch, außer Taake schreibt auf Englisch."
        )
