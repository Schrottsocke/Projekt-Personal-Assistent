"""
Dokument-Scan-Workflow:
1. OCR (pytesseract → Vision-Fallback)
2. KI-Inhaltsanalyse → strukturiertes JSON
3. Durchsuchbares PDF + Drive-Upload in Typen-Ordner
4. Proposals für erkannte Aktionen (Erinnerung, Task, E-Mail-Entwurf)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Dokumenttyp → Drive-Unterordner Mapping
FOLDER_MAP = {
    "rechnung": "Rechnungen",
    "brief": "Briefe",
    "arztbrief": "Arztbriefe",
    "vertrag": "Verträge",
    "behördenschreiben": "Behörden",
    "kontoauszug": "Kontoauszüge",
    "notiz": "Notizen",
    "ausweis": "Ausweise",
    "beleg": "Belege",
}


async def run_document_scan(
    image_bytes: bytes,
    user_key: str,
    chat_id: int,
    bot,
    caption: str = "",
) -> str:
    """
    Führt den vollständigen Dokument-Scan-Workflow aus.

    Returns:
        Telegram-formatierte Zusammenfassung (wird direkt gesendet).
    """
    logger.info(f"Dokument-Scan gestartet für '{user_key}'.")

    # Schritt 1: OCR
    ocr_result = await _run_ocr(image_bytes, bot)
    text = ocr_result["text"]
    confidence = ocr_result["confidence"]
    method = ocr_result["method"]
    words_data = ocr_result.get("words_data")

    if not text.strip():
        logger.warning("OCR hat keinen Text gefunden.")
        text = caption or ""

    # Schritt 2: KI-Analyse
    analysis = await _analyze_document(text, caption, bot.ai_service)

    doc_type_raw = analysis.get("document_type", "Sonstiges")
    doc_type_label = doc_type_raw.strip()
    sender = analysis.get("sender")
    summary = analysis.get("summary", "Kein Inhalt erkennbar.")
    amount = analysis.get("amount")
    doc_date = analysis.get("document_date")
    actions = analysis.get("actions", [])

    # Schritt 3: PDF erstellen + Drive-Upload
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{doc_type_label}.pdf"
    pdf_path = None
    drive_link = None
    drive_file_id = None
    uploaded = None

    try:
        if hasattr(bot, "pdf_service") and bot.pdf_service:
            from config.settings import settings
            pdf_path = bot.pdf_service.create_searchable_pdf(
                image_bytes, text, words_data, filename, save_local=settings.SCAN_SAVE_LOCAL
            )
    except Exception as e:
        logger.error(f"PDF-Erstellung fehlgeschlagen: {e}")

    if pdf_path and hasattr(bot, "drive_service") and bot.drive_service:
        try:
            if bot.drive_service.is_connected(user_key):
                folder_id = await bot.drive_service.get_or_create_document_folder(
                    user_key, doc_type_label.lower()
                )
                uploaded = await bot.drive_service.upload_file(
                    user_key, pdf_path, folder_id
                )
                if uploaded:
                    drive_link = uploaded.get("webViewLink")
                    drive_file_id = uploaded.get("id")
                    logger.info(f"PDF hochgeladen: {drive_link}")

                # Lokal löschen wenn nicht gewünscht
                from config.settings import settings
                if not settings.SCAN_SAVE_LOCAL and pdf_path and pdf_path.exists():
                    pdf_path.unlink(missing_ok=True)
                    pdf_path = None
        except Exception as e:
            logger.error(f"Drive-Upload fehlgeschlagen: {e}")

    # Schritt 4: In DB speichern
    try:
        _save_to_db(
            user_key=user_key,
            doc_type=doc_type_label,
            filename=filename,
            drive_link=drive_link,
            drive_file_id=drive_file_id,
            summary=summary,
            sender=sender,
            amount=amount,
        )
    except Exception as e:
        logger.error(f"DB-Speichern fehlgeschlagen: {e}")

    # Schritt 5: Proposals erstellen
    proposals_created = 0
    for action in actions:
        try:
            await bot.proposal_service.create_proposal(
                user_key=user_key,
                proposal_type=action["type"],
                title=action.get("title", "Aktion"),
                description=action.get("context", ""),
                payload=action,
                created_by="document_scan",
                chat_id=str(chat_id),
                bot=bot,
            )
            proposals_created += 1
        except Exception as e:
            logger.error(f"Proposal-Erstellung fehlgeschlagen: {e}")

    # Antworttext zusammenstellen
    return _format_response(
        doc_type_label=doc_type_label,
        sender=sender,
        summary=summary,
        amount=amount,
        filename=filename,
        drive_link=drive_link,
        pdf_path=pdf_path,
        proposals_created=proposals_created,
        ocr_method=method,
        ocr_confidence=confidence,
        text_length=len(text),
    )


async def _run_ocr(image_bytes: bytes, bot) -> dict:
    """Führt OCR aus, gibt leeres Ergebnis zurück wenn kein OCR-Service."""
    if hasattr(bot, "ocr_service") and bot.ocr_service:
        return await bot.ocr_service.extract_text(image_bytes, bot.ai_service)
    # Fallback: direkt Vision-API
    if hasattr(bot, "ai_service") and bot.ai_service:
        try:
            prompt = (
                "Extrahiere den vollständigen Text aus diesem Dokument-Bild zeichengenau. "
                "Antworte NUR mit dem Text."
            )
            text = await bot.ai_service.analyze_image(image_bytes, prompt)
            return {"text": text, "confidence": 90.0, "method": "vision", "words_data": None}
        except Exception as e:
            logger.error(f"Vision-OCR-Fallback fehlgeschlagen: {e}")
    return {"text": "", "confidence": 0.0, "method": "none", "words_data": None}


async def _analyze_document(text: str, caption: str, ai_service) -> dict:
    """KI-Analyse: Dokumenttyp + strukturierte Aktionen."""
    context = f"Bildunterschrift: {caption}\n\n" if caption else ""
    prompt = f"""{context}Analysiere diesen Dokumenttext und extrahiere strukturierte Daten.
Text:
{text[:3000]}

Antworte NUR mit validem JSON (kein Markdown, keine Erklärungen):
{{
  "document_type": "Rechnung|Brief|Vertrag|Arztbrief|Behördenschreiben|Kontoauszug|Notiz|Ausweis|Beleg|Sonstiges",
  "document_date": "ISO-Datum oder null",
  "sender": "Absender/Firma oder null",
  "summary": "1-2 Sätze was das Dokument ist",
  "amount": "Betrag als String z.B. '49,90 €' oder null",
  "actions": [
    {{
      "type": "reminder_create|task_create|email_compose",
      "title": "Kurzer Aktions-Titel",
      "due_date": "ISO-Datum oder null",
      "amount": "Betrag oder null",
      "priority": "high|medium|low",
      "email_to": "Adresse oder null",
      "email_subject": "Betreff oder null",
      "email_body": "Entwurfstext oder null",
      "context": "Kurze Begründung warum diese Aktion sinnvoll ist"
    }}
  ]
}}"""

    try:
        response = await ai_service._complete(
            prompt=prompt,
            system="Du bist ein Dokumentenanalyse-Assistent. Antworte ausschließlich mit JSON.",
            temperature=0.1,
        )
        # JSON extrahieren (auch wenn trotzdem Markdown dabei)
        raw = response.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Dokumentanalyse JSON-Parse-Fehler: {e}")
        return {"document_type": "Sonstiges", "summary": "Analyse fehlgeschlagen.", "actions": []}
    except Exception as e:
        logger.error(f"Dokumentanalyse fehlgeschlagen: {e}")
        return {"document_type": "Sonstiges", "summary": "Analyse fehlgeschlagen.", "actions": []}


def _save_to_db(
    user_key: str,
    doc_type: str,
    filename: str,
    drive_link: Optional[str],
    drive_file_id: Optional[str],
    summary: Optional[str],
    sender: Optional[str],
    amount: Optional[str],
):
    from src.services.database import ScannedDocument, get_db

    with get_db()() as session:
        doc = ScannedDocument(
            user_key=user_key,
            doc_type=doc_type,
            filename=filename,
            drive_link=drive_link,
            drive_file_id=drive_file_id,
            summary=summary,
            sender=sender,
            amount=amount,
        )
        session.add(doc)


def _format_response(
    doc_type_label: str,
    sender: Optional[str],
    summary: str,
    amount: Optional[str],
    filename: str,
    drive_link: Optional[str],
    pdf_path: Optional[Path],
    proposals_created: int,
    ocr_method: str,
    ocr_confidence: float,
    text_length: int,
) -> str:
    lines = []

    # Titel
    if sender:
        lines.append(f"📄 *Dokument erkannt: {doc_type_label} von {sender}*")
    else:
        lines.append(f"📄 *Dokument erkannt: {doc_type_label}*")

    # Zusammenfassung
    lines.append(f"_{summary}_")

    if amount:
        lines.append(f"💶 Betrag: *{amount}*")

    lines.append("")

    # Speicherung
    lines.append(f"📁 Gespeichert als: `{filename}`")

    if drive_link:
        lines.append(f"🔗 [Drive öffnen]({drive_link})")
    elif pdf_path:
        lines.append(f"💾 Lokal gespeichert (Drive nicht verbunden)")
    else:
        lines.append(f"⚠️ PDF konnte nicht erstellt werden")

    # OCR-Info (nur wenn interessant)
    if ocr_method == "none" or text_length < 10:
        lines.append("⚠️ _Kaum Text erkannt – Bildqualität prüfen_")
    elif ocr_method == "vision":
        lines.append("🤖 _Text via Vision-KI extrahiert_")

    # Proposals
    if proposals_created > 0:
        lines.append("")
        lines.append(f"*{proposals_created} Aktion{'en' if proposals_created != 1 else ''} erkannt:*")
        lines.append("_Sieh dir die Vorschläge unten an und bestätige oder lehne sie ab._")

    return "\n".join(lines)
