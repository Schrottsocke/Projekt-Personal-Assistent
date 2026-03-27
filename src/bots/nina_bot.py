"""Ninas persönlicher Assistent-Bot."""

from config.settings import settings
from src.bots.base_bot import BaseAssistantBot


class NinaBot(BaseAssistantBot):
    def __init__(self):
        config = settings.get_bot_configs()["nina"]
        super().__init__(config)

    def get_system_prompt(self) -> str:
        return (
            "Du bist Ninas persönlicher KI-Assistent. "
            "Du kennst Nina gut und hilfst ihr mit Kalender, Notizen, Erinnerungen und allem anderen. "
            "Du bist warm, verständnisvoll und hilfsbereit – aber ohne unnötige Ausschweifungen. "
            "Wenn du etwas Wichtiges über Nina lernst, merkst du dir das. "
            "Antworte auf Deutsch, außer Nina schreibt auf Englisch."
        )
