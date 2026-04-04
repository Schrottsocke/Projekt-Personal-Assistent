"""GET/POST/PATCH/DELETE /invoices – Rechnungen erstellen und verwalten."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_invoice_service, get_current_user
from api.schemas.invoices import InvoiceCreate, InvoiceOut, InvoiceUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(
    user_key: Annotated[str, Depends(get_current_user)],
    invoice_svc=Depends(get_invoice_service),
    status: Optional[str] = None,
):
    return await invoice_svc.list_invoices(user_key, status_filter=status or "")


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    invoice_svc=Depends(get_invoice_service),
):
    invoice = await invoice_svc.get_invoice(user_key, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return invoice


@router.post("", response_model=InvoiceOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_invoice(
    request: Request,
    body: InvoiceCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    invoice_svc=Depends(get_invoice_service),
):
    try:
        return await invoice_svc.create_invoice(user_key, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{invoice_id}", response_model=InvoiceOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_invoice(
    request: Request,
    invoice_id: str,
    body: InvoiceUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    invoice_svc=Depends(get_invoice_service),
):
    try:
        result = await invoice_svc.update_invoice(
            user_key, invoice_id, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return result


@router.delete("/{invoice_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_invoice(
    request: Request,
    invoice_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    invoice_svc=Depends(get_invoice_service),
):
    deleted = await invoice_svc.delete_invoice(user_key, invoice_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
