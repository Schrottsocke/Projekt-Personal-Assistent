"""
OCR-Service: Text-Extraktion aus Bildern und Dokumenten.
Primär: pytesseract (falls installiert).
Fallback: Vision-API (OpenAI/OpenRouter).

Erweitert um:
- PDF-Unterstützung via pdf2image
- Dokumenten-Klassifikation (Keyword + LLM-Fallback)
- Deadline-/Fristen-Extraktion aus OCR-Text
"""

import asyncio
import logging
import os
import re
from datetime import date, datetime
from typing import Optional

from config.settings import settings

# Concurrency semaphore – limits parallel OCR jobs
_ocr_semaphore: asyncio.Semaphore | None = None


def _get_ocr_semaphore() -> asyncio.Semaphore:
    """Lazy-init semaphore (must be created inside a running event loop)."""
    global _ocr_semaphore
    if _ocr_semaphore is None:
        _ocr_semaphore = asyncio.Semaphore(settings.OCR_MAX_PARALLEL_JOBS)
    return _ocr_semaphore


logger = logging.getLogger(__name__)

# Keyword-Maps für Dokumenten-Klassifikation
_DOCUMENT_KEYWORDS: dict[str, list[str]] = {
    "invoice": [
        "rechnung",
        "rechnungsnummer",
        "rechnungsdatum",
        "invoice",
        "nettobetrag",
        "bruttobetrag",
        "zahlungsziel",
        "umsatzsteuer",
        "mwst",
        "ust-id",
        "bankverbindung",
        "iban",
    ],
    "receipt": [
        "kassenbon",
        "quittung",
        "beleg",
        "receipt",
        "bar bezahlt",
        "kartenzahlung",
        "summe",
        "gesamt",
        "ec-karte",
    ],
    "warranty": [
        "garantie",
        "gewährleistung",
        "warranty",
        "garantieschein",
        "garantiezeitraum",
        "garantiebedingungen",
    ],
    "insurance": [
        "versicherung",
        "police",
        "versicherungsnummer",
        "insurance",
        "versicherungsschein",
        "prämie",
        "selbstbeteiligung",
    ],
    "contract": [
        "vertrag",
        "vereinbarung",
        "contract",
        "laufzeit",
        "kündigungsfrist",
        "vertragspartner",
        "unterschrift",
    ],
}

# Regex-Patterns für deutsche Datumsformate
_DATE_PATTERNS = [
    # "bis zum 15.03.2026", "Frist bis 15.03.2026"
    r"(?:bis\s+zum|frist\s+bis|fällig\s+am|fällig\s+bis|zahlbar\s+bis|deadline|due)\s*:?\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})",
    # Standalone DD.MM.YYYY
    r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})",
    # DD.MM.YY (2-digit year)
    r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2})(?!\d)",
]


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

        Respects OCR_TIMEOUT_SECONDS and OCR_MAX_PARALLEL_JOBS from settings.

        Returns:
            {
                "text": str,
                "confidence": float,   # 0–100
                "method": "tesseract" | "vision" | "none",
                "words_data": dict | None   # pytesseract image_to_data output
            }
        """
        semaphore = _get_ocr_semaphore()
        timeout = settings.OCR_TIMEOUT_SECONDS

        try:
            async with semaphore:
                return await asyncio.wait_for(
                    self._extract_text_inner(image_bytes, ai_service),
                    timeout=timeout,
                )
        except asyncio.TimeoutError:
            logger.error("OCR-Timeout nach %d Sekunden.", timeout)
            return {"text": "", "confidence": 0.0, "method": "none", "words_data": None}

    async def _extract_text_inner(self, image_bytes: bytes, ai_service=None) -> dict:
        """Inner extraction logic (called within semaphore + timeout)."""
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
            try:
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
            finally:
                image.close()
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

    # ------------------------------------------------------------------
    # Extended: File-based extraction, classification, deadline parsing
    # ------------------------------------------------------------------

    async def extract_text_from_file(self, file_path: str, ai_service=None) -> dict:
        """
        Reads a file (PDF or image), converts if needed, runs OCR.

        Returns:
            {
                "text": str,
                "confidence": float,
                "method": str,
                "pages": int,
                "words_data": dict | None,
            }
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return await self._extract_from_pdf(file_path, ai_service)

        # Image path – read bytes and delegate to extract_text
        with open(file_path, "rb") as f:
            image_bytes = f.read()

        result = await self.extract_text(image_bytes, ai_service=ai_service)
        result["pages"] = 1
        return result

    async def _extract_from_pdf(self, file_path: str, ai_service=None) -> dict:
        """Convert PDF pages to images and OCR each page."""
        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("pdf2image nicht installiert – PDF-OCR nicht möglich.")
            return {
                "text": "",
                "confidence": 0.0,
                "method": "none",
                "pages": 0,
                "words_data": None,
            }

        try:
            images = convert_from_path(file_path, dpi=300)
        except Exception as e:
            logger.error(f"PDF-zu-Bild-Konvertierung fehlgeschlagen: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "method": "none",
                "pages": 0,
                "words_data": None,
            }

        import io

        all_texts: list[str] = []
        total_confidence = 0.0
        method = "none"

        for idx, img in enumerate(images):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            page_bytes = buf.getvalue()
            img.close()

            result = await self.extract_text(page_bytes, ai_service=ai_service)
            if result["text"].strip():
                all_texts.append(result["text"])
            total_confidence += result["confidence"]
            if result["method"] != "none":
                method = result["method"]

        page_count = len(images)
        avg_confidence = total_confidence / page_count if page_count else 0.0

        return {
            "text": "\n\n--- Seite ---\n\n".join(all_texts),
            "confidence": avg_confidence,
            "method": method,
            "pages": page_count,
            "words_data": None,
        }

    async def extract_deadline(self, ocr_text: str) -> Optional[date]:
        """
        Extract due dates from OCR text using regex patterns.

        Looks for German date patterns: DD.MM.YYYY, "bis zum DD.MM.YYYY",
        "Fällig am", "Frist bis", etc.

        Returns the earliest future date found, or None.
        """
        if not ocr_text:
            return None

        text_lower = ocr_text.lower()
        today = date.today()
        candidates: list[date] = []

        for pattern in _DATE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                day_s, month_s, year_s = match.group(1), match.group(2), match.group(3)
                try:
                    day = int(day_s)
                    month = int(month_s)
                    year = int(year_s)
                    # Handle 2-digit year
                    if year < 100:
                        year += 2000
                    d = date(year, month, day)
                    if d >= today:
                        candidates.append(d)
                except (ValueError, OverflowError):
                    continue

        if not candidates:
            return None

        return min(candidates)

    async def classify_document(self, ocr_text: str, ai_service=None) -> str:
        """
        Classify document into one of:
        invoice | warranty | insurance | receipt | contract | other

        Uses keyword matching first, LLM fallback if ai_service is provided
        and keyword matching is inconclusive.
        """
        if not ocr_text:
            return "other"

        text_lower = ocr_text.lower()

        # Score each category by keyword hits
        scores: dict[str, int] = {}
        for category, keywords in _DOCUMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            best = max(scores, key=scores.get)  # type: ignore[arg-type]
            # Require at least 2 keyword hits for confident classification
            if scores[best] >= 2:
                logger.info(f"Dokument klassifiziert als '{best}' (Keywords: {scores[best]} Treffer)")
                return best

        # LLM fallback if available
        if ai_service:
            try:
                prompt = (
                    "Klassifiziere das folgende Dokument in genau eine der Kategorien: "
                    "invoice, warranty, insurance, receipt, contract, other.\n"
                    "Antworte NUR mit dem Kategorienamen, ohne Erklärung.\n\n"
                    f"Dokument-Text:\n{ocr_text[:2000]}"
                )
                response = await ai_service.chat(prompt)
                category = response.strip().lower()
                valid = {"invoice", "warranty", "insurance", "receipt", "contract", "other"}
                if category in valid:
                    logger.info(f"Dokument klassifiziert als '{category}' (LLM)")
                    return category
            except Exception as e:
                logger.warning(f"LLM-Klassifikation fehlgeschlagen: {e}")

        # Fall back to best keyword match (even with 1 hit) or "other"
        if scores:
            best = max(scores, key=scores.get)  # type: ignore[arg-type]
            logger.info(f"Dokument klassifiziert als '{best}' (schwache Keyword-Übereinstimmung)")
            return best

        return "other"
