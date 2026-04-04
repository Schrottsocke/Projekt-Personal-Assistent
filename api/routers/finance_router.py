"""Finance-Router: Transactions, Contracts, Budgets, Invoices."""

import csv
import io
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.finance import (
    BudgetAlert,
    BudgetCreate,
    BudgetOut,
    ContractCreate,
    ContractOut,
    ContractSummary,
    ContractUpdate,
    FinanceInvoiceCreate,
    FinanceInvoiceOut,
    FinanceInvoiceUpdate,
    MonthlyOverview,
    TransactionCreate,
    TransactionOut,
)
from config.settings import settings
from src.services.database import (
    Budget,
    Contract,
    FinanceInvoice,
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


# --- Transactions (static routes first) ---


@router.post("/transactions/csv", response_model=list[TransactionOut], status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_csv(
    request: Request,
    file: UploadFile,
    user_key: Annotated[str, Depends(get_current_user)],
):
    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        created = []
        for row in reader:
            txn = Transaction(
                user_id=uid,
                date=row.get("date", row.get("Buchungsdatum", "")),
                amount=float(row.get("amount", row.get("Betrag", "0")).replace(",", ".")),
                description=row.get("description", row.get("Verwendungszweck", "")),
                category=row.get("category"),
                source="csv",
                raw_text=";".join(row.values()),
            )
            db.add(txn)
            created.append(txn)
        db.flush()
        for t in created:
            db.refresh(t)
        return created


@router.get("/transactions/monthly-overview", response_model=MonthlyOverview)
async def monthly_overview(
    user_key: Annotated[str, Depends(get_current_user)],
    year: int,
    month: int,
):
    from datetime import datetime

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        start = datetime(year, month, 1)
        end = datetime(year + (1 if month == 12 else 0), (month % 12) + 1, 1)
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == uid,
                Transaction.date >= start,
                Transaction.date < end,
            )
            .all()
        )
        income = sum(t.amount for t in txns if t.amount > 0)
        expenses = sum(t.amount for t in txns if t.amount < 0)
        by_cat: dict[str, float] = {}
        for t in txns:
            cat = t.category or "Sonstige"
            by_cat[cat] = by_cat.get(cat, 0) + t.amount
        return MonthlyOverview(
            year=year,
            month=month,
            total_income=income,
            total_expenses=abs(expenses),
            by_category=by_cat,
        )


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


@router.delete("/transactions/{transaction_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_transaction(
    request: Request,
    transaction_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == uid).first()
        if not txn:
            raise HTTPException(404, "Transaktion nicht gefunden.")
        db.delete(txn)


# --- Budgets (static routes first) ---


@router.get("/budgets/alerts", response_model=list[BudgetAlert])
async def budget_alerts(
    user_key: Annotated[str, Depends(get_current_user)],
):
    from datetime import datetime

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        budgets = db.query(Budget).filter(Budget.user_id == uid).all()
        now = datetime.utcnow()
        start = datetime(now.year, now.month, 1)
        alerts = []
        for b in budgets:
            spent = sum(
                t.amount
                for t in db.query(Transaction)
                .filter(
                    Transaction.user_id == uid,
                    Transaction.category == b.category,
                    Transaction.date >= start,
                    Transaction.amount < 0,
                )
                .all()
            )
            spent = abs(spent)
            pct = (spent / b.monthly_limit * 100) if b.monthly_limit else 0
            alerts.append(
                BudgetAlert(
                    category=b.category,
                    monthly_limit=b.monthly_limit,
                    spent=spent,
                    percentage=round(pct, 1),
                    over_limit=pct > 100,
                )
            )
        return alerts


@router.post("/budgets", response_model=BudgetOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_budget(
    request: Request,
    body: BudgetCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        b = Budget(user_id=uid, **body.model_dump())
        db.add(b)
        db.flush()
        db.refresh(b)
        return b


@router.get("/budgets", response_model=list[BudgetOut])
async def list_budgets(
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        return db.query(Budget).filter(Budget.user_id == uid).all()


# --- Contracts (static routes first) ---


@router.get("/contracts/summary", response_model=ContractSummary)
async def contract_summary(
    user_key: Annotated[str, Depends(get_current_user)],
):
    from datetime import date, timedelta

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        active = db.query(Contract).filter(Contract.user_id == uid, Contract.status == "active").all()
        total_monthly = 0.0
        for c in active:
            if c.interval == "yearly":
                total_monthly += c.amount / 12
            elif c.interval == "quarterly":
                total_monthly += c.amount / 3
            else:
                total_monthly += c.amount
        cutoff = date.today() + timedelta(days=30)
        expiring = [c for c in active if c.cancellation_deadline and c.cancellation_deadline <= cutoff]
        return ContractSummary(
            total_monthly_cost=round(total_monthly, 2),
            active_count=len(active),
            expiring_soon=expiring,
        )


@router.get("/contracts/expiring", response_model=list[ContractOut])
async def expiring_contracts(
    user_key: Annotated[str, Depends(get_current_user)],
    days: int = 30,
):
    from datetime import date, timedelta

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        cutoff = date.today() + timedelta(days=days)
        return (
            db.query(Contract)
            .filter(
                Contract.user_id == uid,
                Contract.status == "active",
                Contract.cancellation_deadline != None,  # noqa: E711
                Contract.cancellation_deadline <= cutoff,
            )
            .all()
        )


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


@router.patch("/contracts/{contract_id}", response_model=ContractOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_contract(
    request: Request,
    contract_id: int,
    body: ContractUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        c = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == uid).first()
        if not c:
            raise HTTPException(404, "Vertrag nicht gefunden.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(c, k, v)
        db.flush()
        db.refresh(c)
        return c


@router.delete("/contracts/{contract_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_contract(
    request: Request,
    contract_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        c = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == uid).first()
        if not c:
            raise HTTPException(404, "Vertrag nicht gefunden.")
        db.delete(c)


# --- Finance Invoices (static routes first) ---


@router.get("/invoices/overdue", response_model=list[FinanceInvoiceOut])
async def overdue_invoices(
    user_key: Annotated[str, Depends(get_current_user)],
):
    from datetime import date

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        return (
            db.query(FinanceInvoice)
            .filter(
                FinanceInvoice.user_id == uid,
                FinanceInvoice.status == "open",
                FinanceInvoice.due_date < date.today(),
            )
            .all()
        )


@router.post("/invoices", response_model=FinanceInvoiceOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_finance_invoice(
    request: Request,
    body: FinanceInvoiceCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = FinanceInvoice(user_id=uid, **body.model_dump())
        db.add(inv)
        db.flush()
        db.refresh(inv)
        return inv


@router.get("/invoices", response_model=list[FinanceInvoiceOut])
async def list_finance_invoices(
    user_key: Annotated[str, Depends(get_current_user)],
    status: Optional[str] = None,
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid)
        if status:
            q = q.filter(FinanceInvoice.status == status)
        return q.order_by(FinanceInvoice.due_date.desc()).all()


@router.patch("/invoices/{invoice_id}", response_model=FinanceInvoiceOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_finance_invoice(
    request: Request,
    invoice_id: int,
    body: FinanceInvoiceUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = (
            db.query(FinanceInvoice)
            .filter(
                FinanceInvoice.id == invoice_id,
                FinanceInvoice.user_id == uid,
            )
            .first()
        )
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(inv, k, v)
        db.flush()
        db.refresh(inv)
        return inv
