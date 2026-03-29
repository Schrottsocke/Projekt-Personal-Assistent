"""
Dokumenten-Scanner Service: OCR und Klassifikation von Fotos, PDFs und Dokumenten.
Nutzt die bestehende Vision-API (Gemini Flash via OpenRouter) für OCR.
PyPDF2 wird für direkte Text-Extraktion aus PDFs verwendet.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Bekannte Dokumenttypen mit Icons
DOCUMENT_TYPES = {
    "rechnung": "🧾",
    "brief": "✉️",
    "vertrag": "📋",
    "beleg": "🧾",
    "kontoauszug": "🏦",
    "rezept": "🍳",
    "screenshot": "📸",
    "ausweis": "🪪",
    "sonstiges": "📄",
}


class ScannerService:
    """
    Dokumenten-Scanner mit OCR und automatischer Klassifikation.

    Nutzt:
    - Vision-API (Gemini Flash) für Bilder/Screenshots
    - PyPDF2 für direkte Text-Extraktion aus PDFs
    - KI für Klassifikation und Aktions-Erkennung

    Keine externen API-Keys nötig – nutzt bestehende Vision-API.
    """

    # ------------------------------------------------------------------
    # Bild-OCR
    # ------------------------------------------------------------------

    async def scan_image(self, image_bytes: bytes, ai_service) -> dict:
        """
        Extrahiert Text aus einem Bild und klassifiziert das Dokument.

        Args:
            image_bytes: Rohe Bilddaten (JPEG, PNG, etc.)
            ai_service: AIService-Instanz für Vision-API-Zugriff

        Returns:
            Dict mit: text, doc_type, confidence, actions (list)
        """
        prompt = """Analysiere dieses Dokument/Bild sorgfältig.

1. Extrahiere den vollständigen Text (OCR)
2. Klassifiziere den Dokumenttyp: rechnung | brief | vertrag | beleg | kontoauszug | rezept | screenshot | ausweis | sonstiges
3. Erkenne mögliche Aktionen: Aufgaben, Termine, Fristen, Beträge die bezahlt werden müssen

Antworte NUR mit diesem JSON:
{
  "text": "vollständiger extrahierter Text",
  "doc_type": "rechnung|brief|vertrag|beleg|kontoauszug|rezept|screenshot|ausweis|sonstiges",
  "confidence": 0.0-1.0,
  "summary": "Kurze Beschreibung was das Dokument ist",
  "actions": [
    {"type": "task|reminder|calendar", "content": "Aktionsbeschreibung", "due": "Datum falls vorhanden oder null"}
  ],
  "amount": "Betrag falls Rechnung/Beleg, sonst null",
  "sender": "Absender falls erkennbar, sonst null"
}"""

        try:
            import base64
            import json as _json

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ]

            from config.settings import settings

            response = await ai_service._complete(
                messages=messages,
                model=settings.VISION_MODEL,
            )

            # JSON aus Antwort extrahieren
            try:
                result = _json.loads(response)
            except _json.JSONDecodeError:
                # Fallback: Antwort als plain text behandeln
                result = {
                    "text": response,
                    "doc_type": "sonstiges",
                    "confidence": 0.5,
                    "summary": "Dokument analysiert",
                    "actions": [],
                    "amount": None,
                    "sender": None,
                }

            return result

        except Exception as e:
            logger.error(f"Scanner scan_image Fehler: {e}")
            return {
                "text": "",
                "doc_type": "sonstiges",
                "confidence": 0.0,
                "summary": "Analyse fehlgeschlagen",
                "actions": [],
                "amount": None,
                "sender": None,
            }

    # ------------------------------------------------------------------
    # PDF-Verarbeitung
    # ------------------------------------------------------------------

    async def scan_pdf(self, pdf_bytes: bytes, ai_service) -> dict:
        """
        Extrahiert Text aus einem PDF und klassifiziert es.

        Versucht zuerst direkte Text-Extraktion (PyPDF2),
        fällt bei Bild-PDFs auf Vision-API zurück.

        Returns:
            Dict mit: text, doc_type, confidence, actions, pages
        """
        text = ""
        pages = 0

        # Schritt 1: Direkte Text-Extraktion
        try:
            import io
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = len(reader.pages)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
            text = text.strip()
        except ImportError:
            logger.warning("PyPDF2 nicht installiert – PDF-Text-Extraktion nicht verfügbar")
        except Exception as e:
            logger.warning(f"PDF-Text-Extraktion fehlgeschlagen: {e}")

        if text and len(text) > 50:
            # Text vorhanden → KI-Klassifikation ohne Vision
            result = await self._classify_text(text, ai_service)
            result["pages"] = pages
            return result
        else:
            # Kein Text (Bild-PDF) → Vision-API auf erste Seite
            logger.info("PDF ohne extrahierbaren Text – verwende Vision-API")
            first_page_bytes = await self._pdf_first_page_to_image(pdf_bytes)
            if first_page_bytes:
                result = await self.scan_image(first_page_bytes, ai_service)
            else:
                result = {
                    "text": "",
                    "doc_type": "sonstiges",
                    "confidence": 0.0,
                    "summary": "PDF konnte nicht verarbeitet werden",
                    "actions": [],
                    "amount": None,
                    "sender": None,
                }
            result["pages"] = pages
            return result

    async def _classify_text(self, text: str, ai_service) -> dict:
        """Klassifiziert extrahierten Text via KI."""
        prompt = f"""Analysiere diesen Text aus einem Dokument.

Text:
{text[:3000]}

Klassifiziere und extrahiere Aktionen. Antworte NUR mit diesem JSON:
{{
  "text": "text",
  "doc_type": "rechnung|brief|vertrag|beleg|kontoauszug|rezept|screenshot|sonstiges",
  "confidence": 0.0-1.0,
  "summary": "Kurze Beschreibung",
  "actions": [
    {{"type": "task|reminder|calendar", "content": "Aktionsbeschreibung", "due": "Datum oder null"}}
  ],
  "amount": "Betrag falls Rechnung/Beleg, sonst null",
  "sender": "Absender falls erkennbar, sonst null"
}}"""

        try:
            import json as _json

            response = await ai_service._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            result = _json.loads(response)
            result["text"] = text
            return result
        except Exception as e:
            logger.error(f"Text-Klassifikation Fehler: {e}")
            return {
                "text": text,
                "doc_type": "sonstiges",
                "confidence": 0.5,
                "summary": "Dokument verarbeitet",
                "actions": [],
                "amount": None,
                "sender": None,
            }

    async def _pdf_first_page_to_image(self, pdf_bytes: bytes) -> Optional[bytes]:
        """Konvertiert die erste PDF-Seite in ein Bild (benötigt pdf2image/poppler)."""
        try:
            from pdf2image import convert_from_bytes
            import io

            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=150)
            if not images:
                return None
            buf = io.BytesIO()
            images[0].save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except ImportError:
            logger.warning("pdf2image nicht installiert – Bild-PDF-Verarbeitung nicht verfügbar")
            return None
        except Exception as e:
            logger.warning(f"PDF-zu-Bild-Konvertierung fehlgeschlagen: {e}")
            return None

    # ------------------------------------------------------------------
    # Aktions-Routing
    # ------------------------------------------------------------------

    async def classify_and_route(self, scan_result: dict, user_key: str, bot, chat_id=None) -> str:
        """
        Wertet das Scan-Ergebnis aus und erstellt Proposals für erkannte Aktionen.

        Args:
            scan_result: Rückgabe von scan_image() oder scan_pdf()
            user_key: Bot-User-Key
            bot: Bot-Instanz für Proposal-Erstellung

        Returns:
            Zusammenfassung der erkannten Aktionen als Telegram-Markdown.
        """
        doc_type = scan_result.get("doc_type", "sonstiges")
        summary = scan_result.get("summary", "Dokument verarbeitet")
        actions = scan_result.get("actions", [])
        amount = scan_result.get("amount")
        sender = scan_result.get("sender")
        icon = DOCUMENT_TYPES.get(doc_type, "📄")

        lines = [
            f"{icon} *{summary}*",
            f"Typ: {doc_type.capitalize()}",
        ]
        if sender:
            lines.append(f"Von: {sender}")
        if amount:
            lines.append(f"Betrag: {amount}")

        if not actions:
            lines.append("\n_Keine Aktionen erkannt._")
            return "\n".join(lines)

        lines.append(f"\n*Erkannte Aktionen ({len(actions)}):*")

        for action in actions:
            action_type = action.get("type", "task")
            content = action.get("content", "")
            due = action.get("due")

            if not content:
                continue

            # Proposal für jede Aktion erstellen
            try:
                if hasattr(bot, "proposal_service") and bot.proposal_service:
                    payload = {
                        "content": content,
                        "due": due,
                        "source": f"scanner:{doc_type}",
                    }
                    proposal_type = {
                        "task": "task_create",
                        "reminder": "reminder_create",
                        "calendar": "calendar_create",
                    }.get(action_type, "task_create")

                    await bot.proposal_service.create_proposal(
                        proposal_type=proposal_type,
                        title=content[:80],
                        description=f"Aus {doc_type}: {summary}",
                        payload=payload,
                        user_key=user_key,
                        created_by="scanner",
                        chat_id=str(chat_id) if chat_id else None,
                        bot=bot,
                    )
                type_icon = {"task": "📋", "reminder": "⏰", "calendar": "📅"}.get(action_type, "•")
                due_str = f" (bis {due})" if due else ""
                lines.append(f"{type_icon} {content}{due_str}")
            except Exception as e:
                logger.error(f"Scanner Proposal-Erstellung fehlgeschlagen: {e}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Formatierung
    # ------------------------------------------------------------------

    @staticmethod
    def format_scan_result(scan_result: dict) -> str:
        """Formatiert ein Scan-Ergebnis als Telegram-Markdown (ohne Proposals)."""
        doc_type = scan_result.get("doc_type", "sonstiges")
        summary = scan_result.get("summary", "")
        text = scan_result.get("text", "")[:500]
        icon = DOCUMENT_TYPES.get(doc_type, "📄")
        confidence = scan_result.get("confidence", 0)

        lines = [
            f"{icon} *Scan-Ergebnis*",
            f"Typ: {doc_type.capitalize()} ({int(confidence * 100)}% Konfidenz)",
        ]
        if summary:
            lines.append(f"\n_{summary}_")
        if text:
            lines.append(f"\n*Erkannter Text:*\n```\n{text}\n```")

        return "\n".join(lines)
