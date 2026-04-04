"""GET/POST/PATCH/DELETE /contacts + CSV import/export"""

import csv
import io
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_contacts_service, get_current_user
from api.schemas.contacts import ContactCreate, ContactOut, ContactUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ─── CSV Export / Import (must be before /{contact_id} routes) ───


@router.get("/export")
async def export_contacts(
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    """Export all user contacts as CSV."""
    contacts = await contacts_svc.list_contacts(user_key, limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "email", "phone", "notes", "tags", "source"])
    for c in contacts:
        tags = ";".join(c.get("tags", [])) if isinstance(c.get("tags"), list) else (c.get("tags") or "")
        writer.writerow(
            [
                c.get("name", ""),
                c.get("email", ""),
                c.get("phone", ""),
                c.get("notes", ""),
                tags,
                c.get("source", ""),
            ]
        )

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )


@router.post("/import")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def import_contacts(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    """Import contacts from CSV with duplicate check by name+email."""
    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="Keine Datei")

    content = await file.read()
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    except Exception:
        raise HTTPException(status_code=400, detail="CSV konnte nicht gelesen werden")

    existing_contacts = await contacts_svc.list_contacts(user_key, limit=10000)
    existing_keys = {(c.get("name", ""), c.get("email")) for c in existing_contacts}

    imported = 0
    skipped = 0
    for row in reader:
        name = row.get("name", "").strip()
        email = row.get("email", "").strip() or None
        if not name or (name, email) in existing_keys:
            skipped += 1
            continue

        tags_raw = row.get("tags", "").strip()
        tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []

        contact_data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "phone": row.get("phone", "").strip() or None,
            "notes": row.get("notes", "").strip() or None,
            "tags": tags,
            "source": row.get("source", "").strip() or "csv-import",
        }
        await contacts_svc.upsert_contact(user_key, contact_data)
        existing_keys.add((name, email))
        imported += 1

    return {"imported": imported, "skipped": skipped}


# ─── CRUD ────────────────────────────────────────────────────


@router.get("", response_model=list[ContactOut])
async def list_contacts(
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await contacts_svc.list_contacts(user_key, query=q or "", limit=limit, offset=offset)


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(
    contact_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    contact = await contacts_svc.get_contact(user_key, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden.")
    return contact


@router.post("", response_model=ContactOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_contact(
    request: Request,
    body: ContactCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    return await contacts_svc.upsert_contact(user_key, body.model_dump())


@router.patch("/{contact_id}", response_model=ContactOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_contact(
    request: Request,
    contact_id: str,
    body: ContactUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    data = body.model_dump(exclude_unset=True)
    data["id"] = contact_id
    result = await contacts_svc.upsert_contact(user_key, data)
    if not result:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden.")
    return result


@router.delete("/{contact_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_contact(
    request: Request,
    contact_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    contacts_svc=Depends(get_contacts_service),
):
    deleted = await contacts_svc.delete_contact(user_key, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden.")
