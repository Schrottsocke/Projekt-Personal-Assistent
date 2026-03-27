"""
TTS-Service: Text-to-Speech via gTTS (Google TTS, kostenlos, kein API-Key).
Sendet Audio als Telegram-Sprachnachricht (OGG) oder Audiodatei (MP3).

Opt-in per User: /tts oder "Antworte als Sprachnachricht"
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech mit gTTS.
    Speichert Audio temporär und löscht es nach dem Senden.
    """

    def __init__(self):
        self._available = False
        self._check_availability()

    def _check_availability(self):
        try:
            import gtts  # noqa: F401

            self._available = True
            logger.info("TTS-Service: gTTS verfügbar.")
        except ImportError:
            logger.warning("TTS-Service: gTTS nicht installiert (pip install gTTS). TTS deaktiviert.")

    @property
    def available(self) -> bool:
        return self._available

    async def synthesize(self, text: str, lang: str = "de") -> Optional[Path]:
        """
        Wandelt Text in Sprache um.
        Returns: Pfad zur MP3-Datei (muss nach dem Senden gelöscht werden), oder None bei Fehler.
        """
        if not self._available:
            return None

        # Text auf sinnvolle Länge kürzen (gTTS-Limit ~5000 Zeichen)
        text = text[:4000].strip()
        if not text:
            return None

        # Markdown-Formatierung entfernen (gTTS liest * und _ vor)
        text = self._clean_markdown(text)

        try:
            from gtts import gTTS

            tts = gTTS(text=text, lang=lang, slow=False)

            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", prefix="tts_", delete=False, dir=Path("data/documents"))
            tmp.close()
            tts.save(tmp.name)
            logger.debug(f"TTS generiert: {tmp.name} ({len(text)} Zeichen)")
            return Path(tmp.name)
        except Exception as e:
            logger.error(f"TTS-Fehler: {e}")
            return None

    def _clean_markdown(self, text: str) -> str:
        """Entfernt Markdown-Zeichen die gTTS vorlesen würde."""
        import re

        text = re.sub(r"\*+", "", text)  # Bold/Italic
        text = re.sub(r"_+", "", text)  # Italic
        text = re.sub(r"`+", "", text)  # Code
        text = re.sub(r"#+\s", "", text)  # Headers
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # Links → Text
        text = re.sub(r"•\s", "- ", text)
        return text.strip()

    async def send_voice(self, bot_app, chat_id: int, text: str) -> bool:
        """
        Synthesizes text and sends as audio message.
        Returns True on success.
        """
        path = await self.synthesize(text)
        if not path:
            return False
        try:
            with open(path, "rb") as audio:
                await bot_app.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio,
                    title="Sprachantwort",
                    performer="Assistent",
                )
            return True
        except Exception as e:
            logger.error(f"TTS-Send-Fehler: {e}")
            return False
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
