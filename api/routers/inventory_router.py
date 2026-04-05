"""Inventory-Router: Items, Warranties, Document-Scanning."""

from datetime import date, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.inventory import (
    DocumentScanResult,
    DocumentSearchResult,
    InventoryItemCreate,
    InventoryItemOut,
    InventoryItemUpdate,
    ReceiptLinkRequest,
    RoomListOut,
    ValueSummary,
    WarrantyCreate,
    WarrantyOut,
    WarrantyUpdate,
)
from config.settings import settings
from src.services.database import (
    HouseholdDocument,
    InventoryItem,
    ScannedDocument,
    UserProfile,
    Warranty,
    get_db,
)
from src.services.storage_service import StorageService

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _resolve_user_id(db, user_key: str) -> int:
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden.")
    return profile.id


@router.get("/health")
async def health():
    return {"status": "ok", "module": "inventory"}


# --- Widget Summary ---


@router.get("/widget-summary")
async def widget_summary(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        cutoff = date.today() + timedelta(days=30)

        # Expiring warranties (within 30 days)
        expiring = (
            db.query(Warranty)
            .filter(
                Warranty.user_id == uid,
                Warranty.warranty_end != None,  # noqa: E711
                Warranty.warranty_end <= cutoff,
                Warranty.warranty_end >= date.today(),
            )
            .count()
        )

        # Unprocessed documents (no category assigned)
        unprocessed = (
            db.query(ScannedDocument)
            .filter(
                ScannedDocument.user_key == user_key,
                ScannedDocument.category == None,  # noqa: E711
            )
            .count()
        )

        # Next deadline from documents
        next_doc = (
            db.query(ScannedDocument)
            .filter(
                ScannedDocument.user_key == user_key,
                ScannedDocument.deadline != None,  # noqa: E711
                ScannedDocument.deadline >= date.today(),
            )
            .order_by(ScannedDocument.deadline.asc())
            .first()
        )

        return {
            "expiring_warranties_count": expiring,
            "unprocessed_documents_count": unprocessed,
            "next_deadline": next_doc.deadline.isoformat() if next_doc else None,
            "next_deadline_doc": next_doc.filename if next_doc else None,
        }


# --- Items ---


@router.get("/items/value-summary", response_model=ValueSummary)
async def value_summary(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        items = db.query(InventoryItem).filter(InventoryItem.user_id == uid).all()
        total = sum(i.value or 0 for i in items)
        return ValueSummary(total_value=round(total, 2), item_count=len(items))


@router.get("/items", response_model=list[InventoryItemOut])
async def list_items(
    user_key: Annotated[str, Depends(get_current_user)],
    room: Optional[str] = None,
    workspace_id: Optional[int] = None,
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(InventoryItem).filter(InventoryItem.user_id == uid)
        if room:
            q = q.filter(InventoryItem.room == room)
        if workspace_id:
            q = q.filter(InventoryItem.workspace_id == workspace_id)
        return q.order_by(InventoryItem.created_at.desc()).all()


@router.get("/items/{item_id}", response_model=InventoryItemOut)
async def get_item(item_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
        if not item:
            raise HTTPException(404, "Gegenstand nicht gefunden.")
        return item


@router.post("/items", response_model=InventoryItemOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_item(
    request: Request,
    body: InventoryItemCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = InventoryItem(user_id=uid, **body.model_dump())
        db.add(item)
        db.flush()
        db.refresh(item)
        return item


@router.post("/items-with-photo", response_model=InventoryItemOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_item_with_photo(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    name: str = Form(...),
    description: Optional[str] = Form(None),
    room: Optional[str] = Form(None),
    value: Optional[float] = Form(None),
    purchase_date: Optional[date] = Form(None),
    receipt_doc_id: Optional[int] = Form(None),
    workspace_id: Optional[int] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    """Create inventory item with optional photo upload in a single request."""
    photo_url = None
    if photo and photo.filename:
        from pathlib import Path as _P

        ext = _P(photo.filename).suffix.lower()
        if ext not in ALLOWED_PHOTO_EXTENSIONS:
            raise HTTPException(400, f"Fototyp '{ext}' nicht erlaubt. Erlaubt: {ALLOWED_PHOTO_EXTENSIONS}")
        if photo.content_type and photo.content_type not in ALLOWED_PHOTO_TYPES:
            raise HTTPException(400, f"MIME-Type '{photo.content_type}' nicht erlaubt.")
        data = await photo.read()
        storage = StorageService()
        photo_url = await storage.save(user_key, photo.filename, data, photo.content_type or "")

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = InventoryItem(
            user_id=uid,
            name=name,
            description=description,
            room=room,
            photo_url=photo_url,
            value=value,
            purchase_date=purchase_date,
            receipt_doc_id=receipt_doc_id,
            workspace_id=workspace_id,
        )
        db.add(item)
        db.flush()
        db.refresh(item)
        return item


@router.patch("/items/{item_id}", response_model=InventoryItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_item(
    request: Request,
    item_id: int,
    body: InventoryItemUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
        if not item:
            raise HTTPException(404, "Gegenstand nicht gefunden.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        db.flush()
        db.refresh(item)
        return item


@router.post("/items/{item_id}/photo", response_model=InventoryItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_item_photo(
    request: Request,
    item_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    photo: UploadFile = File(...),
):
    """Upload a photo for an existing inventory item."""
    from pathlib import Path as _P

    ext = _P(photo.filename or "").suffix.lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise HTTPException(400, f"Fototyp '{ext}' nicht erlaubt. Erlaubt: {ALLOWED_PHOTO_EXTENSIONS}")
    if photo.content_type and photo.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(400, f"MIME-Type '{photo.content_type}' nicht erlaubt.")

    data = await photo.read()
    storage = StorageService()
    photo_url = await storage.save(user_key, photo.filename or "photo.jpg", data, photo.content_type or "")

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
        if not item:
            raise HTTPException(404, "Gegenstand nicht gefunden.")
        item.photo_url = photo_url
        db.flush()
        db.refresh(item)
        return item


@router.get("/rooms", response_model=RoomListOut)
async def list_rooms(user_key: Annotated[str, Depends(get_current_user)]):
    """Return distinct room values from the user's inventory items."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        rows = (
            db.query(InventoryItem.room)
            .filter(InventoryItem.user_id == uid, InventoryItem.room != None, InventoryItem.room != "")  # noqa: E711
            .distinct()
            .order_by(InventoryItem.room)
            .all()
        )
        return RoomListOut(rooms=[r[0] for r in rows])


@router.post("/items/{item_id}/link-receipt", response_model=InventoryItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def link_receipt(
    request: Request,
    item_id: int,
    body: ReceiptLinkRequest,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Link an existing HouseholdDocument as receipt for an inventory item."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
        if not item:
            raise HTTPException(404, "Gegenstand nicht gefunden.")
        doc = (
            db.query(HouseholdDocument)
            .filter(HouseholdDocument.id == body.document_id, HouseholdDocument.user_id == uid)
            .first()
        )
        if not doc:
            raise HTTPException(404, "Dokument nicht gefunden oder gehoert einem anderen Benutzer.")
        item.receipt_doc_id = body.document_id
        db.flush()
        db.refresh(item)
        return item


@router.delete("/items/{item_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_item(
    request: Request,
    item_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.user_id == uid).first()
        if not item:
            raise HTTPException(404, "Gegenstand nicht gefunden.")
        db.delete(item)


# --- Warranties ---


@router.get("/warranties/expiring", response_model=list[WarrantyOut])
async def expiring_warranties(user_key: Annotated[str, Depends(get_current_user)], days: int = 30):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        cutoff = date.today() + timedelta(days=days)
        return (
            db.query(Warranty)
            .filter(
                Warranty.user_id == uid,
                Warranty.warranty_end != None,  # noqa: E711
                Warranty.warranty_end <= cutoff,
                Warranty.warranty_end >= date.today(),
            )
            .order_by(Warranty.warranty_end.asc())
            .all()
        )


@router.get("/warranties", response_model=list[WarrantyOut])
async def list_warranties(
    user_key: Annotated[str, Depends(get_current_user)],
    status: Optional[str] = None,
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(Warranty).filter(Warranty.user_id == uid)
        if status == "active":
            q = q.filter(
                (Warranty.warranty_end == None)  # noqa: E711
                | (Warranty.warranty_end >= date.today())
            )
        elif status == "expired":
            q = q.filter(Warranty.warranty_end < date.today())
        return q.order_by(Warranty.created_at.desc()).all()


@router.get("/warranties/{warranty_id}", response_model=WarrantyOut)
async def get_warranty(warranty_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        w = db.query(Warranty).filter(Warranty.id == warranty_id, Warranty.user_id == uid).first()
        if not w:
            raise HTTPException(404, "Garantie nicht gefunden.")
        return w


@router.post("/warranties", response_model=WarrantyOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_warranty(
    request: Request,
    body: WarrantyCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        w = Warranty(user_id=uid, **body.model_dump())
        db.add(w)
        db.flush()
        db.refresh(w)
        return w


@router.patch("/warranties/{warranty_id}", response_model=WarrantyOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_warranty(
    request: Request,
    warranty_id: int,
    body: WarrantyUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        w = db.query(Warranty).filter(Warranty.id == warranty_id, Warranty.user_id == uid).first()
        if not w:
            raise HTTPException(404, "Garantie nicht gefunden.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(w, k, v)
        db.flush()
        db.refresh(w)
        return w


@router.delete("/warranties/{warranty_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_warranty(
    request: Request,
    warranty_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        w = db.query(Warranty).filter(Warranty.id == warranty_id, Warranty.user_id == uid).first()
        if not w:
            raise HTTPException(404, "Garantie nicht gefunden.")
        db.delete(w)


# --- Document Scanning (#648, #654) ---

CATEGORY_KEYWORDS = {
    "rechnung": ["rechnung", "invoice", "zahlung", "betrag"],
    "vertrag": ["vertrag", "contract", "laufzeit", "kuendigung"],
    "garantie": ["garantie", "warranty", "gewaehrleistung"],
    "kassenbon": ["kassenbon", "quittung", "bon", "receipt"],
    "versicherung": ["versicherung", "police", "insurance"],
    "behoerde": ["bescheid", "finanzamt", "amt", "behoerde"],
}

ACTION_MAP = {
    "rechnung": "expense",
    "vertrag": "contract",
    "garantie": "warranty",
    "kassenbon": "expense",
    "versicherung": "contract",
    "behoerde": "task",
}


def _classify_document(doc) -> tuple[str, str]:
    text = ((doc.ocr_text or "") + " " + (doc.doc_type or "") + " " + (doc.summary or "")).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat, ACTION_MAP.get(cat, "task")
    return "sonstiges", "task"


@router.post("/documents/classify", response_model=DocumentScanResult)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def classify_document(
    request: Request,
    document_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        doc = (
            db.query(ScannedDocument)
            .filter(
                ScannedDocument.id == document_id,
                ScannedDocument.user_key == user_key,
            )
            .first()
        )
        if not doc:
            raise HTTPException(404, "Dokument nicht gefunden.")
        cat, action = _classify_document(doc)
        doc.category = cat
        db.flush()
        return DocumentScanResult(
            document_id=doc.id,
            category=cat,
            deadline=doc.deadline,
            ocr_confidence=doc.ocr_confidence,
            summary=doc.summary,
            suggested_action=action,
        )


@router.post("/documents/scan-to-action", response_model=DocumentScanResult)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def scan_to_action(
    request: Request,
    document_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        doc = (
            db.query(ScannedDocument)
            .filter(
                ScannedDocument.id == document_id,
                ScannedDocument.user_key == user_key,
            )
            .first()
        )
        if not doc:
            raise HTTPException(404, "Dokument nicht gefunden.")
        cat, action = _classify_document(doc)
        if not doc.category:
            doc.category = cat
            db.flush()
        return DocumentScanResult(
            document_id=doc.id,
            category=doc.category or cat,
            deadline=doc.deadline,
            ocr_confidence=doc.ocr_confidence,
            summary=doc.summary,
            suggested_action=action,
        )


@router.get("/documents/search", response_model=list[DocumentSearchResult])
async def search_documents(
    user_key: Annotated[str, Depends(get_current_user)],
    q: str = "",
):
    if not q or len(q) < 2:
        raise HTTPException(400, "Suchbegriff muss mind. 2 Zeichen haben.")
    with get_db()() as db:
        return (
            db.query(ScannedDocument)
            .filter(
                ScannedDocument.user_key == user_key,
                ScannedDocument.ocr_text.ilike(f"%{q}%"),
            )
            .order_by(ScannedDocument.scanned_at.desc())
            .limit(50)
            .all()
        )
