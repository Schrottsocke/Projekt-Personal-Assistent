"""CRUD /documents – Household Documents mit Multipart Upload und Storage-Backend."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.household_documents import HouseholdDocumentList, HouseholdDocumentOut
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _get_storage_service():
    """Lazy-init StorageService (kein async init noetig)."""
    from api.dependencies import _svc
    from src.services.storage_service import StorageService

    if "storage" not in _svc:
        drive = _svc.get("drive")
        _svc["storage"] = StorageService(drive_service=drive)
    return _svc["storage"]


def _get_user_id(user_key: str) -> int:
    """Resolve user_key to user_profiles.id."""
    from src.services.database import UserProfile, get_db

    db = get_db()
    with db() as session:
        user = session.query(UserProfile).filter_by(user_key=user_key).first()
        if not user:
            raise HTTPException(status_code=404, detail="User nicht gefunden.")
        return user.id


async def _run_ocr_background(doc_id: int, file_path: str, user_key: str):
    """Background-Task: OCR ausfuehren, klassifizieren, Frist extrahieren, Task/Notification erstellen."""
    try:
        from api.dependencies import _svc
        from src.services.database import HouseholdDocument, get_db

        storage = _svc.get("storage")
        ocr = _svc.get("ocr")
        ai = _svc.get("ai")
        if not storage or not ocr:
            logger.warning("OCR-Background: Storage oder OCR-Service nicht verfuegbar.")
            return

        file_data = await storage.read(file_path)
        if not file_data:
            logger.warning("OCR-Background: Datei nicht lesbar: %s", file_path)
            return

        # 1. OCR
        result = await ocr.extract_text(file_data, ai)
        ocr_text = result.get("text", "")

        # 2. Classify
        category = await ocr.classify_document(ocr_text, ai)

        # 3. Extract deadline
        deadline = await ocr.extract_deadline(ocr_text)

        # 4. Update document in DB
        doc_title = None
        db = get_db()
        with db() as session:
            doc = session.query(HouseholdDocument).filter_by(id=doc_id).first()
            if doc:
                doc.ocr_text = ocr_text[:10000] if ocr_text else None
                if category and category != "other":
                    doc.category = category
                if deadline:
                    doc.deadline_date = deadline
                doc_title = doc.title
                logger.info(
                    "OCR abgeschlossen fuer Dokument #%d (%d Zeichen, Kategorie=%s, Frist=%s)",
                    doc_id,
                    len(ocr_text),
                    category,
                    deadline,
                )

        # 5. Create task if deadline found
        if deadline and doc_title:
            task_svc = _svc.get("task")
            if task_svc:
                try:
                    await task_svc.create_task(
                        user_key=user_key,
                        title=f"Frist: {doc_title} am {deadline.isoformat()}",
                        due_date=datetime(deadline.year, deadline.month, deadline.day, tzinfo=timezone.utc),
                        priority="high",
                    )
                    logger.info("Frist-Task erstellt fuer Dokument #%d", doc_id)
                except Exception as e:
                    logger.warning("Task-Erstellung fehlgeschlagen fuer Dokument #%d: %s", doc_id, e)

        # 6. Create notification
        notif_svc = _svc.get("notification")
        if notif_svc and doc_title:
            try:
                await notif_svc.create(
                    user_key=user_key,
                    type="document",
                    title=f"Dokument verarbeitet: {category} - {doc_title}",
                    message=f"OCR abgeschlossen. Kategorie: {category}"
                    + (f", Frist: {deadline.isoformat()}" if deadline else ""),
                )
            except Exception as e:
                logger.warning("Notification-Erstellung fehlgeschlagen fuer Dokument #%d: %s", doc_id, e)

    except Exception as e:
        logger.error("OCR-Background-Fehler fuer Dokument #%d: %s", doc_id, e)


@router.get("", response_model=HouseholdDocumentList)
async def list_household_documents(
    user_key: Annotated[str, Depends(get_current_user)],
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Listet alle Household Documents des Users."""
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        query = session.query(HouseholdDocument).filter(HouseholdDocument.user_id == user_id)
        if category:
            query = query.filter(HouseholdDocument.category == category)
        total = query.count()
        items = query.order_by(HouseholdDocument.created_at.desc()).offset(offset).limit(limit).all()
        return HouseholdDocumentList(
            items=[HouseholdDocumentOut.model_validate(d) for d in items],
            total=total,
        )


class DocumentStatsOut(BaseModel):
    """Response-Schema fuer Dokument-Statistiken."""

    categories: dict[str, int]
    upcoming_deadlines: int


@router.get("/stats", response_model=DocumentStatsOut)
async def get_document_stats(
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Statistiken: Anzahl pro Kategorie + Dokumente mit Frist in den naechsten 30 Tagen."""
    from sqlalchemy import func
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        # Counts per category
        rows = (
            session.query(HouseholdDocument.category, func.count(HouseholdDocument.id))
            .filter(HouseholdDocument.user_id == user_id)
            .group_by(HouseholdDocument.category)
            .all()
        )
        categories = {cat or "uncategorized": cnt for cat, cnt in rows}

        # Upcoming deadlines (next 30 days)
        today = date.today()
        deadline_cutoff = today + timedelta(days=30)
        upcoming = (
            session.query(func.count(HouseholdDocument.id))
            .filter(
                HouseholdDocument.user_id == user_id,
                HouseholdDocument.deadline_date >= today,
                HouseholdDocument.deadline_date <= deadline_cutoff,
            )
            .scalar()
        )

    return DocumentStatsOut(categories=categories, upcoming_deadlines=upcoming or 0)


@router.get("/{doc_id}", response_model=HouseholdDocumentOut)
async def get_household_document(
    doc_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Einzelnes Dokument abrufen."""
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        doc = (
            session.query(HouseholdDocument)
            .filter(HouseholdDocument.id == doc_id, HouseholdDocument.user_id == user_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        return HouseholdDocumentOut.model_validate(doc)


@router.post("/upload", response_model=HouseholdDocumentOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_household_document(
    request: Request,
    background_tasks: BackgroundTasks,
    user_key: Annotated[str, Depends(get_current_user)],
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    run_ocr: bool = Form(True),
    storage=Depends(_get_storage_service),
):
    """Datei hochladen, in Storage speichern, Metadaten in household_documents anlegen."""
    from src.services.database import HouseholdDocument, get_db

    # Pre-check file size if available (avoids loading oversized files into RAM)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu gross: {file.size / 1024 / 1024:.1f} MB (max {settings.MAX_UPLOAD_SIZE_MB} MB).",
        )

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="Leere Datei.")

    # Fallback size check for chunked uploads where file.size was None
    if len(file_data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Datei zu gross: {len(file_data) / 1024 / 1024:.1f} MB (max {settings.MAX_UPLOAD_SIZE_MB} MB).",
        )

    # Validate + save to storage
    try:
        file_path = await storage.save(
            user_key=user_key,
            filename=file.filename or "upload",
            data=file_data,
            content_type=file.content_type or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create DB entry
    user_id = _get_user_id(user_key)
    doc_title = title or file.filename or "Unbenanntes Dokument"

    db = get_db()
    with db() as session:
        doc = HouseholdDocument(
            user_id=user_id,
            title=doc_title[:300],
            category=category,
            file_path=file_path,
        )
        session.add(doc)
        session.flush()
        doc_id = doc.id
        result = HouseholdDocumentOut.model_validate(doc)

    # Trigger OCR in background
    if run_ocr:
        background_tasks.add_task(_run_ocr_background, doc_id, file_path, user_key)

    return result


@router.delete("/{doc_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_household_document(
    request: Request,
    doc_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    storage=Depends(_get_storage_service),
):
    """Dokument loeschen (DB + Storage)."""
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        doc = (
            session.query(HouseholdDocument)
            .filter(HouseholdDocument.id == doc_id, HouseholdDocument.user_id == user_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        file_path = doc.file_path
        session.delete(doc)

    # Delete from storage (best effort)
    if file_path:
        try:
            await storage.delete(file_path)
        except Exception as e:
            logger.warning("Storage-Delete fehlgeschlagen fuer %s: %s", file_path, e)


@router.get("/{doc_id}/download")
async def download_household_document(
    doc_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    storage=Depends(_get_storage_service),
):
    """Original-Datei herunterladen."""
    from fastapi.responses import Response
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        doc = (
            session.query(HouseholdDocument)
            .filter(HouseholdDocument.id == doc_id, HouseholdDocument.user_id == user_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        file_path = doc.file_path
        title = doc.title

    if not file_path:
        raise HTTPException(status_code=404, detail="Keine Datei vorhanden.")

    data = await storage.read(file_path)
    if data is None:
        raise HTTPException(status_code=404, detail="Datei nicht im Storage gefunden.")

    # Determine content type from extension
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    content_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    ct = content_types.get(ext, "application/octet-stream")

    return Response(content=data, media_type=ct, headers={"Content-Disposition": f'attachment; filename="{title}"'})


@router.post("/{doc_id}/reprocess", response_model=HouseholdDocumentOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def reprocess_document(
    request: Request,
    doc_id: int,
    background_tasks: BackgroundTasks,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Re-run OCR + Klassifikation + Frist-Extraktion fuer ein bestehendes Dokument."""
    from src.services.database import HouseholdDocument, get_db

    user_id = _get_user_id(user_key)
    db = get_db()
    with db() as session:
        doc = (
            session.query(HouseholdDocument)
            .filter(HouseholdDocument.id == doc_id, HouseholdDocument.user_id == user_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")
        if not doc.file_path:
            raise HTTPException(status_code=400, detail="Keine Datei vorhanden fuer OCR.")

        file_path = doc.file_path
        result = HouseholdDocumentOut.model_validate(doc)

    background_tasks.add_task(_run_ocr_background, doc_id, file_path, user_key)
    return result
