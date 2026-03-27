"""
ApiBotShim: Leichter Proxy damit AIService in der API genutzt werden kann.

AIService erwartet ein bot-Objekt mit Service-Attributen (bot.shopping_service etc.).
Der Shim stellt diese Attribute bereit ohne ein echter Telegram-Bot zu sein.
"""


class ApiBotShim:
    """Simuliert das Bot-Interface für AIService-Aufrufe aus der API."""

    name = "api"

    def __init__(self, **services):
        for key, svc in services.items():
            setattr(self, key, svc)
        # Fehlende Attribute als None defaults
        _optional = [
            "ai_service",
            "memory_service",
            "calendar_service",
            "notes_service",
            "reminder_service",
            "proposal_service",
            "task_service",
            "document_service",
            "tts_service",
            "spotify_service",
            "smarthome_service",
            "chefkoch_service",
            "drive_service",
            "shopping_service",
            "email_service",
            "scanner_service",
            "mobility_service",
            "ocr_service",
            "pdf_service",
        ]
        for attr in _optional:
            if not hasattr(self, attr):
                setattr(self, attr, None)

    async def send_message(self, chat_id, text, **kwargs):
        """No-op: API hat keinen Telegram-Chat."""
        pass

    @property
    def app(self):
        return None
