"""GET/POST /documents – Dokumenten-Eingang mit OCR, PDF-Erstellung und Drive-Ablage."""

import json as _json
import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_ai_service,
    get_current_user,
    get_drive_service,
    get_memory_service,
    get_ocr_service,
    get_pdf_service,
    get_task_service,
)
from api.schemas.documents import DocumentListResponse, DocumentOut
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_key: Annotated[str, Depends(get_current_user)],
    doc_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Listet verarbeitete Dokumente aus der DB."""
    from src.services.database import ScannedDocument, get_db

    db = get_db()
    with db() as session:
        query = session.query(ScannedDocument).filter(ScannedDocument.user_key == user_key)
        if doc_type:
            query = query.filter(ScannedDocument.doc_type == doc_type)
        total = query.count()
        items = query.order_by(ScannedDocument.scanned_at.desc()).offset(offset).limit(limit).all()
        return DocumentListResponse(
            items=[DocumentOut.model_validate(d) for d in items],
            total=total,
        )


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Einzelnes Dokument mit OCR-Text."""
    from src.services.database import ScannedDocument, get_db

    db = get_db()
    with db() as session:
        doc = (
            session.query(ScannedDocument)
            .filter(ScannedDocument.id == doc_id, ScannedDocument.user_key == user_key)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        return DocumentOut.model_validate(doc)


@router.post("/upload", response_model=DocumentOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_document(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    file: UploadFile = File(...),
    ai_service=Depends(get_ai_service),
    ocr_service=Depends(get_ocr_service),
    pdf_service=Depends(get_pdf_service),
    drive_service=Depends(get_drive_service),
):
    """Dokument hochladen, OCR ausfuehren, PDF erstellen, in Drive ablegen."""
    from src.services.database import ScannedDocument, get_db

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Leere Datei.")

    # 1. OCR via OcrService (Tesseract -> Vision-Fallback)
    ocr_result = await ocr_service.extract_text(image_bytes, ai_service)
    ocr_text = ocr_result.get("text", "")
    words_data = ocr_result.get("words_data")

    # 2. KI-Analyse fuer Dokumenttyp
    doc_type = "Sonstiges"
    summary = ""
    sender = None
    amount = None
    if ocr_text.strip():
        try:
            analysis_prompt = f"""Analysiere diesen Dokumenttext und antworte NUR mit validem JSON:
{{
  "document_type": "Rechnung|Brief|Vertrag|Arztbrief|Sonstiges",
  "summary": "1-2 Saetze",
  "sender": "Absender oder null",
  "amount": "Betrag oder null"
}}

Text:
{ocr_text[:3000]}"""
            messages = [
                {
                    "role": "system",
                    "content": "Du bist ein Dokumentenanalyse-Assistent. Antworte ausschliesslich mit JSON.",
                },
                {"role": "user", "content": analysis_prompt},
            ]
            raw = await ai_service._complete(messages=messages, json_mode=True)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            analysis = _json.loads(raw)
            doc_type = analysis.get("document_type", "Sonstiges")
            summary = analysis.get("summary", "")
            sender = analysis.get("sender")
            amount = analysis.get("amount")
        except Exception as exc:
            logger.warning("Dokumentanalyse fehlgeschlagen: %s", exc)
            summary = ocr_text[:200]

    # 3. PDF erstellen
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{doc_type}.pdf"
    pdf_path = None
    try:
        pdf_path = pdf_service.create_searchable_pdf(
            image_bytes, ocr_text, words_data, filename, save_local=settings.SCAN_SAVE_LOCAL
        )
    except Exception as exc:
        logger.error("PDF-Erstellung fehlgeschlagen: %s", exc)

    # 4. Drive-Upload (optional, graceful)
    drive_link = None
    drive_file_id = None
    if pdf_path:
        try:
            if drive_service.is_connected(user_key):
                folder_id = await drive_service.get_or_create_document_folder(user_key, doc_type.lower())
                uploaded = await drive_service.upload_file(user_key, pdf_path, folder_id)
                if uploaded:
                    drive_link = uploaded.get("webViewLink")
                    drive_file_id = uploaded.get("id")
                # Lokal loeschen wenn nicht gewuenscht
                if not settings.SCAN_SAVE_LOCAL and pdf_path.exists():
                    pdf_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Drive-Upload fehlgeschlagen: %s", exc)

    # 5. In DB speichern
    db = get_db()
    with db() as session:
        doc = ScannedDocument(
            user_key=user_key,
            doc_type=doc_type,
            filename=filename,
            drive_link=drive_link,
            drive_file_id=drive_file_id,
            summary=summary,
            sender=sender,
            amount=amount,
            ocr_text=ocr_text[:10000] if ocr_text else None,
        )
        session.add(doc)
        session.flush()
        result = DocumentOut.model_validate(doc)

    return result


@router.post("/upload-multi", response_model=DocumentOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_multi_page(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    files: List[UploadFile] = File(...),
    ai_service=Depends(get_ai_service),
    ocr_service=Depends(get_ocr_service),
    pdf_service=Depends(get_pdf_service),
    drive_service=Depends(get_drive_service),
):
    """Mehrere Bilder als mehrseitiges PDF hochladen."""
    import io
    from src.services.database import ScannedDocument, get_db

    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien hochgeladen.")

    all_ocr_texts = []
    page_pdfs = []

    for page_file in files:
        page_bytes = await page_file.read()
        if not page_bytes:
            continue

        # OCR pro Seite
        ocr_result = await ocr_service.extract_text(page_bytes, ai_service)
        page_text = ocr_result.get("text", "")
        words_data = ocr_result.get("words_data")
        all_ocr_texts.append(page_text)

        # PDF pro Seite erstellen (im Speicher)
        try:
            page_pdf_bytes = pdf_service._build_pdf(page_bytes, page_text, words_data)
            page_pdfs.append(page_pdf_bytes)
        except Exception as exc:
            logger.warning("PDF fuer Seite fehlgeschlagen: %s", exc)

    if not page_pdfs:
        raise HTTPException(status_code=400, detail="Keine Seiten konnten verarbeitet werden.")

    # Texte zusammenfuehren
    combined_text = "\n\n--- Seite ---\n\n".join(all_ocr_texts)

    # KI-Analyse ueber den kombinierten Text
    doc_type = "Sonstiges"
    summary = ""
    sender = None
    amount = None
    if combined_text.strip():
        try:
            analysis_prompt = f"""Analysiere diesen Dokumenttext und antworte NUR mit validem JSON:
{{
  "document_type": "Rechnung|Brief|Vertrag|Arztbrief|Sonstiges",
  "summary": "1-2 Saetze",
  "sender": "Absender oder null",
  "amount": "Betrag oder null"
}}

Text:
{combined_text[:3000]}"""
            messages = [
                {
                    "role": "system",
                    "content": "Du bist ein Dokumentenanalyse-Assistent. Antworte ausschliesslich mit JSON.",
                },
                {"role": "user", "content": analysis_prompt},
            ]
            raw = await ai_service._complete(messages=messages, json_mode=True)
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            analysis = _json.loads(raw)
            doc_type = analysis.get("document_type", "Sonstiges")
            summary = analysis.get("summary", "")
            sender = analysis.get("sender")
            amount = analysis.get("amount")
        except Exception as exc:
            logger.warning("Dokumentanalyse fehlgeschlagen: %s", exc)
            summary = combined_text[:200]

    # PDFs zusammenfuehren
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{doc_type}_{len(page_pdfs)}S.pdf"
    pdf_path = None
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for pdf_bytes in page_pdfs:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages:
                writer.add_page(page)

        save_dir = settings.SCANS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = save_dir / filename
        with open(pdf_path, "wb") as f:
            writer.write(f)
    except Exception as exc:
        logger.error("PDF-Merge fehlgeschlagen: %s", exc)

    # Drive-Upload
    drive_link = None
    drive_file_id = None
    if pdf_path:
        try:
            if drive_service.is_connected(user_key):
                folder_id = await drive_service.get_or_create_document_folder(user_key, doc_type.lower())
                uploaded = await drive_service.upload_file(user_key, pdf_path, folder_id)
                if uploaded:
                    drive_link = uploaded.get("webViewLink")
                    drive_file_id = uploaded.get("id")
                if not settings.SCAN_SAVE_LOCAL and pdf_path.exists():
                    pdf_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Drive-Upload fehlgeschlagen: %s", exc)

    # DB speichern
    db = get_db()
    with db() as session:
        doc = ScannedDocument(
            user_key=user_key,
            doc_type=doc_type,
            filename=filename,
            drive_link=drive_link,
            drive_file_id=drive_file_id,
            summary=summary,
            sender=sender,
            amount=amount,
            ocr_text=combined_text[:10000] if combined_text else None,
        )
        session.add(doc)
        session.flush()
        result = DocumentOut.model_validate(doc)

    return result


@router.post("/{doc_id}/actions")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def trigger_document_action(
    request: Request,
    doc_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    task_service=Depends(get_task_service),
    memory_service=Depends(get_memory_service),
):
    """Folgeaktion aus Dokument ausloesen (Task, Memory, E-Mail-Entwurf)."""
    from src.services.database import ScannedDocument, get_db

    db = get_db()
    with db() as session:
        doc = (
            session.query(ScannedDocument)
            .filter(ScannedDocument.id == doc_id, ScannedDocument.user_key == user_key)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

        # Daten vor Session-Schliessung extrahieren
        doc_data = {
            "doc_type": doc.doc_type,
            "summary": doc.summary or "",
            "sender": doc.sender,
            "amount": doc.amount,
            "ocr_text": doc.ocr_text or "",
            "filename": doc.filename,
        }

    body = await request.json()
    action = body.get("action", "create_task")

    if action == "create_task":
        title = body.get("title") or f"{doc_data['doc_type']}: {doc_data['summary'][:60]}"
        description = body.get("description", "")
        if not description:
            parts = [f"Aus Dokument: {doc_data['filename']}"]
            if doc_data["sender"]:
                parts.append(f"Von: {doc_data['sender']}")
            if doc_data["amount"]:
                parts.append(f"Betrag: {doc_data['amount']}")
            if doc_data["summary"]:
                parts.append(doc_data["summary"])
            description = "\n".join(parts)
        task = await task_service.create_task(
            user_key=user_key,
            title=title[:200],
            description=description,
            priority=body.get("priority", "medium"),
        )
        return {"status": "ok", "action": "create_task", "doc_id": doc_id, "task": task}

    elif action == "save_memory":
        fact_parts = [f"Dokument gescannt: {doc_data['doc_type']}"]
        if doc_data["sender"]:
            fact_parts.append(f"von {doc_data['sender']}")
        if doc_data["summary"]:
            fact_parts.append(f"– {doc_data['summary']}")
        if doc_data["amount"]:
            fact_parts.append(f"(Betrag: {doc_data['amount']})")
        fact = " ".join(fact_parts)
        memory_id = await memory_service.add_fact(fact, user_key)
        return {
            "status": "ok",
            "action": "save_memory",
            "doc_id": doc_id,
            "memory_id": memory_id,
            "message": "Dokumentinhalt wurde gespeichert.",
        }

    elif action == "draft_email":
        subject = f"Betr.: {doc_data['doc_type']}"
        if doc_data["sender"]:
            subject += f" von {doc_data['sender']}"
        email_body = "Sehr geehrte Damen und Herren,\n\n"
        email_body += "bezugnehmend auf Ihr Schreiben"
        if doc_data["sender"]:
            email_body += f" ({doc_data['sender']})"
        email_body += ":\n\n"
        if doc_data["summary"]:
            email_body += f"{doc_data['summary']}\n\n"
        email_body += "Mit freundlichen Gruessen"
        return {
            "status": "ok",
            "action": "draft_email",
            "doc_id": doc_id,
            "draft": {"subject": subject, "body": email_body, "to": ""},
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action}")
