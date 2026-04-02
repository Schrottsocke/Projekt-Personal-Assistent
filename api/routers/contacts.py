"""GET/POST/PATCH/DELETE /contacts"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_contacts_service, get_current_user
from api.schemas.contacts import ContactCreate, ContactOut, ContactUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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
