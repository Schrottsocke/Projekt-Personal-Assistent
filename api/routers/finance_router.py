"""Finance-Router: Transactions, Contracts, Budgets, Invoices."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.finance import (
    ContractCreate,
    ContractOut,
    TransactionCreate,
    TransactionOut,
)
from config.settings import settings
from src.services.database import (
    Contract,
    Transaction,
    UserProfile,
    get_db,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _resolve_user_id(db, user_key: str) -> int:
    """user_key → user_profiles.id aufloesen."""
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden.")
    return profile.id


# --- Health ---

@router.get("/health")
async def health():
    return {"status": "ok", "module": "finance"}


# --- Transactions ---

@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    user_key: Annotated[str, Depends(get_current_user)],
    category: Optional[str] = None,
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(Transaction).filter(Transaction.user_id == uid)
        if category:
            q = q.filter(Transaction.category == category)
        return q.order_by(Transaction.date.desc()).all()


@router.post("/transactions", response_model=TransactionOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_transaction(
    request: Request,
    body: TransactionCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        txn = Transaction(user_id=uid, **body.model_dump())
        db.add(txn)
        db.flush()
        db.refresh(txn)
        return txn


# --- Contracts ---

@router.get("/contracts", response_model=list[ContractOut])
async def list_contracts(
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        return db.query(Contract).filter(Contract.user_id == uid).order_by(Contract.created_at.desc()).all()


@router.post("/contracts", response_model=ContractOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_contract(
    request: Request,
    body: ContractCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        contract = Contract(user_id=uid, **body.model_dump())
        db.add(contract)
        db.flush()
        db.refresh(contract)
        return contract
