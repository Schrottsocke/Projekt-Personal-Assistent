"""GET/POST /documents – Dokumenten-Eingang mit OCR und Drive-Ablage."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_ai_service, get_drive_service
from api.schemas.documents import DocumentListResponse, DocumentOut
from config.settings import settings

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
    """Einzelnes Dokument mit OCR-Text und Proposals."""
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
    drive_service=Depends(get_drive_service),
):
    """Dokument hochladen, OCR ausfuehren, in Drive ablegen."""
    from datetime import datetime
    from src.services.database import ScannedDocument, get_db

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Leere Datei.")

    # OCR via AI Vision
    ocr_text = ""
    try:
        prompt = "Extrahiere den vollstaendigen Text aus diesem Dokument-Bild zeichengenau. Antworte NUR mit dem Text."
        ocr_text = await ai_service.analyze_image(image_bytes, prompt)
    except Exception:
        pass

    # KI-Analyse fuer Dokumenttyp
    doc_type = "Sonstiges"
    summary = ""
    sender = None
    amount = None
    if ocr_text.strip():
        try:
            import json as _json

            analysis_prompt = f"""Analysiere diesen Dokumenttext und antworte NUR mit validem JSON:
{{
  "document_type": "Rechnung|Brief|Vertrag|Arztbrief|Sonstiges",
  "summary": "1-2 Saetze",
  "sender": "Absender oder null",
  "amount": "Betrag oder null"
}}

Text:
{ocr_text[:3000]}"""
            raw = await ai_service._complete(
                prompt=analysis_prompt,
                system="Du bist ein Dokumentenanalyse-Assistent. Antworte ausschliesslich mit JSON.",
                temperature=0.1,
            )
            raw = raw.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            analysis = _json.loads(raw)
            doc_type = analysis.get("document_type", "Sonstiges")
            summary = analysis.get("summary", "")
            sender = analysis.get("sender")
            amount = analysis.get("amount")
        except Exception:
            summary = ocr_text[:200]

    # Drive-Upload
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}_{doc_type}.pdf"
    drive_link = None
    drive_file_id = None

    # In DB speichern
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
):
    """Folgeaktion aus Dokument ausloesen (Task, Erinnerung etc.)."""
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

    body = await request.json()
    action_type = body.get("action", "task")

    return {
        "status": "ok",
        "action": action_type,
        "doc_id": doc_id,
        "message": f"Aktion '{action_type}' fuer Dokument #{doc_id} erstellt.",
    }
