"""
OCR-Service: Text-Extraktion aus Bildern.
Primär: pytesseract (falls installiert).
Fallback: Vision-API (OpenAI/OpenRouter).
"""

import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class OcrService:
    """
    Extrahiert Text aus Bildern.
    Gibt dict zurück: {text, confidence, method, words_data}
    """

    def __init__(self):
        self.confidence_threshold = settings.OCR_CONFIDENCE_THRESHOLD
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.info("pytesseract/Tesseract nicht verfügbar – Vision-API als Fallback.")
            return False

    async def extract_text(self, image_bytes: bytes, ai_service=None) -> dict:
        """
        Extrahiert Text aus image_bytes.

        Returns:
            {
                "text": str,
                "confidence": float,   # 0–100
                "method": "tesseract" | "vision" | "none",
                "words_data": dict | None   # pytesseract image_to_data output
            }
        """
        if self._tesseract_available:
            result = await self._extract_tesseract(image_bytes)
            if result and result["confidence"] >= self.confidence_threshold:
                return result
            if result and result["text"].strip():
                # Tesseract hat etwas erkannt, aber Konfidenz niedrig → Vision-Fallback
                logger.info(
                    f"Tesseract-Konfidenz {result['confidence']:.0f} < {self.confidence_threshold} "
                    f"→ Vision-API Fallback."
                )

        # Vision-API Fallback
        if ai_service:
            return await self._extract_vision(image_bytes, ai_service)

        logger.warning("Weder Tesseract noch Vision-API verfügbar – OCR nicht möglich.")
        return {"text": "", "confidence": 0.0, "method": "none", "words_data": None}

    async def _extract_tesseract(self, image_bytes: bytes) -> Optional[dict]:
        try:
            import pytesseract
            from PIL import Image
            import io
            import pandas as pd

            image = Image.open(io.BytesIO(image_bytes))

            # Vorverarbeitung: Graustufenbild verbessert OCR-Qualität
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")

            # Volltext
            text = pytesseract.image_to_string(image, lang="deu+eng", config="--oem 3 --psm 3")

            # Wortdaten für PDF-Text-Layer
            words_data = pytesseract.image_to_data(
                image,
                lang="deu+eng",
                config="--oem 3 --psm 3",
                output_type=pytesseract.Output.DICT,
            )

            # Konfidenz berechnen (Durchschnitt aller Wörter mit conf > 0)
            confs = [c for c in words_data["conf"] if isinstance(c, (int, float)) and c > 0]
            confidence = sum(confs) / len(confs) if confs else 0.0

            logger.info(f"Tesseract OCR: {len(text.split())} Wörter, Konfidenz {confidence:.0f}%")
            return {
                "text": text,
                "confidence": confidence,
                "method": "tesseract",
                "words_data": words_data,
                "image_size": image.size,  # (width, height) für PDF-Koordinaten
            }
        except ImportError:
            self._tesseract_available = False
            return None
        except Exception as e:
            logger.error(f"Tesseract-Fehler: {e}")
            return None

    async def _extract_vision(self, image_bytes: bytes, ai_service) -> dict:
        try:
            prompt = (
                "Extrahiere den vollständigen Text aus diesem Dokument-Bild zeichengenau. "
                "Behalte die originale Formatierung (Zeilenumbrüche, Absätze) so gut wie möglich bei. "
                "Antworte NUR mit dem extrahierten Text, ohne Kommentare oder Erklärungen."
            )
            text = await ai_service.analyze_image(image_bytes, prompt)
            logger.info(f"Vision-API OCR: {len(text.split())} Wörter extrahiert.")
            return {
                "text": text,
                "confidence": 90.0,  # Vision-API als zuverlässig angenommen
                "method": "vision",
                "words_data": None,
            }
        except Exception as e:
            logger.error(f"Vision-OCR-Fehler: {e}")
            return {"text": "", "confidence": 0.0, "method": "none", "words_data": None}
