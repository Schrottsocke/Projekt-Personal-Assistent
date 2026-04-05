"""Finance-Router: Transactions, Contracts, Budgets, Invoices."""

import csv
import io
import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.finance import (
    BudgetAlert,
    BudgetCreate,
    BudgetOut,
    CategoryBreakdown,
    ContractCreate,
    ContractOut,
    ContractSummary,
    ContractUpdate,
    CsvImportResult,
    DetectedContract,
    FinanceInvoiceCreate,
    FinanceInvoiceOut,
    FinanceInvoiceUpdate,
    FinanceWidgetSummary,
    HealthOut,
    InvoiceStats,
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

logger = logging.getLogger(__name__)

# --- Auto-Categorization Keywords (#645) ---

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Lebensmittel": ["rewe", "aldi", "lidl", "edeka", "netto", "penny", "kaufland", "dm ", "rossmann"],
    "Restaurant": ["restaurant", "pizz", "sushi", "burger", "mcdonalds", "lieferando", "uber eats"],
    "Transport": ["tankstelle", "shell", "aral", "total", "db ", "bahn", "flixbus", "tier", "lime"],
    "Wohnen": ["miete", "strom", "gas", "heizung", "stadtwerke", "hausgeld"],
    "Versicherung": ["versicherung", "haftpflicht", "hausrat", "krankenk"],
    "Kommunikation": ["telekom", "vodafone", "o2", "mobilfunk", "internet", "1&1"],
    "Unterhaltung": ["netflix", "spotify", "disney", "amazon prime", "kino", "steam"],
    "Gesundheit": ["apotheke", "arzt", "zahnarzt", "physioth"],
    "Kleidung": ["h&m", "zara", "zalando", "c&a", "deichmann"],
    "Gehalt": ["gehalt", "lohn", "salary", "wage"],
}


def _auto_categorize(description: str) -> Optional[str]:
    """Match transaction description to a category via keyword scoring."""
    if not description:
        return None
    text = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return None


def _is_duplicate(db, uid: int, txn_date: datetime, amount: float, raw_text: str) -> bool:
    """Check if a transaction with same date, amount, and raw_text already exists."""
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == uid,
            Transaction.date == txn_date,
            Transaction.amount == amount,
            Transaction.raw_text == raw_text,
        )
        .first()
    )
    return existing is not None


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _resolve_user_id(db, user_key: str) -> int:
    """user_key → user_profiles.id aufloesen."""
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden.")
    return profile.id


# --- Health ---


@router.get("/health", response_model=HealthOut)
async def health():
    return {"status": "ok", "module": "finance"}


# --- Widget Summary ---


@router.get("/widget-summary", response_model=FinanceWidgetSummary)
async def widget_summary(
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        # Spending this month
        txns = (
            db.query(Transaction)
            .filter(Transaction.user_id == uid, Transaction.date >= month_start, Transaction.amount < 0)
            .all()
        )
        spending = round(abs(sum(t.amount for t in txns)), 2)

        # Budget total
        budgets = db.query(Budget).filter(Budget.user_id == uid).all()
        budget_total = round(sum(b.monthly_limit for b in budgets), 2)

        # Next payment (contract with nearest next_billing)
        next_contract = (
            db.query(Contract)
            .filter(
                Contract.user_id == uid,
                Contract.status == "active",
                Contract.next_billing != None,  # noqa: E711
                Contract.next_billing >= date.today(),
            )
            .order_by(Contract.next_billing.asc())
            .first()
        )

        # Open invoices
        open_invoices = (
            db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid, FinanceInvoice.status == "open").count()
        )

        return {
            "spending_this_month": spending,
            "budget_total": budget_total,
            "next_payment_date": next_contract.next_billing.isoformat() if next_contract else None,
            "next_payment_amount": next_contract.amount if next_contract else None,
            "open_invoices_count": open_invoices,
        }


# --- Transactions (static routes first) ---


@router.post("/transactions/csv", response_model=CsvImportResult, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upload_csv(
    request: Request,
    file: UploadFile,
    user_key: Annotated[str, Depends(get_current_user)],
    skip_duplicates: bool = True,
):
    """CSV-Import mit Auto-Kategorisierung und Duplikat-Erkennung (#645)."""
    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    rows = list(reader)

    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        imported = 0
        skipped = 0

        for row in rows:
            date_str = row.get("date", row.get("Buchungsdatum", ""))
            try:
                parsed_date = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                parsed_date = datetime.utcnow()

            amount = float(row.get("amount", row.get("Betrag", "0")).replace(",", "."))
            description = row.get("description", row.get("Verwendungszweck", ""))
            raw_text = ";".join(row.values())

            # Duplicate detection
            if skip_duplicates and _is_duplicate(db, uid, parsed_date, amount, raw_text):
                skipped += 1
                continue

            # Auto-categorize if no category provided
            category = row.get("category") or _auto_categorize(description)

            txn = Transaction(
                user_id=uid,
                date=parsed_date,
                amount=amount,
                description=description,
                category=category,
                source="csv",
                raw_text=raw_text,
            )
            db.add(txn)
            imported += 1

        db.flush()
        return CsvImportResult(
            imported=imported,
            skipped_duplicates=skipped,
            total_rows=len(rows),
        )


@router.get("/transactions/monthly-overview", response_model=MonthlyOverview)
async def monthly_overview(
    user_key: Annotated[str, Depends(get_current_user)],
    year: int,
    month: int,
):
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


@router.get("/transactions/by-category", response_model=CategoryBreakdown)
async def transactions_by_category(
    user_key: Annotated[str, Depends(get_current_user)],
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """Ausgaben aggregiert nach Kategorie (#645)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(Transaction).filter(Transaction.user_id == uid, Transaction.amount < 0)
        if year and month:
            start = datetime(year, month, 1)
            end = datetime(year + (1 if month == 12 else 0), (month % 12) + 1, 1)
            q = q.filter(Transaction.date >= start, Transaction.date < end)
        elif year:
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
            q = q.filter(Transaction.date >= start, Transaction.date < end)
        txns = q.all()
        by_cat: dict[str, float] = {}
        for t in txns:
            cat = t.category or "Sonstige"
            by_cat[cat] = round(by_cat.get(cat, 0) + abs(t.amount), 2)
        return {"categories": by_cat, "total": round(sum(by_cat.values()), 2)}


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


@router.post("/contracts/{contract_id}/calculate-deadlines", response_model=ContractOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def calculate_contract_deadlines(
    request: Request,
    contract_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Kuendigungsfrist und naechste Abrechnung auto-berechnen (#646)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        c = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == uid).first()
        if not c:
            raise HTTPException(404, "Vertrag nicht gefunden.")

        # Calculate next billing date if not set
        if not c.next_billing and c.start_date:
            today = date.today()
            billing = c.start_date
            if c.interval == "monthly":
                step = timedelta(days=30)
            elif c.interval == "quarterly":
                step = timedelta(days=91)
            else:  # yearly
                step = timedelta(days=365)
            while billing < today:
                billing = billing + step
            c.next_billing = billing

        # Calculate cancellation deadline from end_date and cancellation_days
        if c.cancellation_days and c.end_date and not c.cancellation_deadline:
            c.cancellation_deadline = c.end_date - timedelta(days=c.cancellation_days)
        elif c.cancellation_days and c.next_billing and not c.cancellation_deadline:
            c.cancellation_deadline = c.next_billing - timedelta(days=c.cancellation_days)

        # Auto-expire if end_date is past
        if c.end_date and c.end_date < date.today() and c.status == "active":
            c.status = "expired"

        db.flush()
        db.refresh(c)
        return c


@router.get("/contracts/detect-from-transactions", response_model=list[DetectedContract])
async def detect_contracts_from_transactions(
    user_key: Annotated[str, Depends(get_current_user)],
    min_occurrences: int = 3,
):
    """Wiederkehrende Zahlungen erkennen und als potenzielle Vertraege vorschlagen (#646)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        txns = (
            db.query(Transaction)
            .filter(Transaction.user_id == uid, Transaction.amount < 0)
            .order_by(Transaction.date.asc())
            .all()
        )

        # Group by description + similar amount (rounded to 2 decimals)
        groups: dict[str, list] = {}
        for t in txns:
            desc = (t.description or "").strip().lower()[:60]
            if not desc:
                continue
            key = f"{desc}|{abs(round(t.amount, 2))}"
            groups.setdefault(key, []).append(t)

        suggestions = []
        for key, group in groups.items():
            if len(group) < min_occurrences:
                continue
            desc_part, amount_str = key.rsplit("|", 1)
            # Check if already tracked as contract
            existing = (
                db.query(Contract)
                .filter(
                    Contract.user_id == uid,
                    Contract.amount == float(amount_str),
                    Contract.status == "active",
                )
                .first()
            )
            if existing:
                continue

            # Detect interval from date gaps
            dates = sorted([t.date for t in group])
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 30
            if avg_gap < 45:
                interval = "monthly"
            elif avg_gap < 120:
                interval = "quarterly"
            else:
                interval = "yearly"

            suggestions.append(
                {
                    "description": group[0].description,
                    "amount": abs(round(float(amount_str), 2)),
                    "interval": interval,
                    "occurrences": len(group),
                    "first_seen": dates[0].isoformat(),
                    "last_seen": dates[-1].isoformat(),
                    "category": group[0].category,
                }
            )

        return sorted(suggestions, key=lambda s: s["occurrences"], reverse=True)


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


@router.get("/invoices/stats", response_model=InvoiceStats)
async def invoice_stats(
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Rechnungsstatistik: offen, bezahlt, ueberfaellig, Gesamtbetraege (#647)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        invoices = db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid).all()
        open_inv = [i for i in invoices if i.status == "open"]
        paid_inv = [i for i in invoices if i.status == "paid"]
        overdue_inv = [i for i in invoices if i.status == "overdue"]
        draft_inv = [i for i in invoices if i.status == "draft"]
        return {
            "open": {"count": len(open_inv), "total": round(sum(i.total for i in open_inv), 2)},
            "paid": {"count": len(paid_inv), "total": round(sum(i.total for i in paid_inv), 2)},
            "overdue": {"count": len(overdue_inv), "total": round(sum(i.total for i in overdue_inv), 2)},
            "draft": {"count": len(draft_inv), "total": round(sum(i.total for i in draft_inv), 2)},
        }


def _generate_invoice_number(db, uid: int) -> str:
    """Auto-generate invoice number: RE-YYYY-NNNN (#647)."""
    year = date.today().year
    prefix = f"RE-{year}-"
    last = (
        db.query(FinanceInvoice)
        .filter(
            FinanceInvoice.user_id == uid,
            FinanceInvoice.invoice_number.like(f"{prefix}%"),
        )
        .order_by(FinanceInvoice.invoice_number.desc())
        .first()
    )
    if last and last.invoice_number:
        try:
            seq = int(last.invoice_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


@router.post("/invoices", response_model=FinanceInvoiceOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_finance_invoice(
    request: Request,
    body: FinanceInvoiceCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Rechnung erstellen mit Auto-Nummerierung (#647)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        data = body.model_dump()
        # Auto-generate invoice number if not provided
        if not data.get("invoice_number"):
            data["invoice_number"] = _generate_invoice_number(db, uid)
        # Default issue_date to today
        if not data.get("issue_date"):
            data["issue_date"] = date.today()
        inv = FinanceInvoice(user_id=uid, **data)
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


@router.get("/invoices/{invoice_id}", response_model=FinanceInvoiceOut)
async def get_finance_invoice(
    invoice_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id, FinanceInvoice.user_id == uid).first()
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden.")
        return inv


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


@router.post("/invoices/{invoice_id}/mark-paid", response_model=FinanceInvoiceOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def mark_invoice_paid(
    request: Request,
    invoice_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    payment_date: Optional[date] = None,
):
    """Rechnung als bezahlt markieren (#647)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id, FinanceInvoice.user_id == uid).first()
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden.")
        if inv.status == "paid":
            raise HTTPException(400, "Rechnung ist bereits bezahlt.")
        inv.status = "paid"
        inv.payment_date = payment_date or date.today()
        db.flush()
        db.refresh(inv)
        return inv


@router.post("/invoices/{invoice_id}/mark-overdue", response_model=FinanceInvoiceOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def mark_invoice_overdue(
    request: Request,
    invoice_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Rechnung als ueberfaellig markieren (#647)."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id, FinanceInvoice.user_id == uid).first()
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden.")
        if inv.status != "open":
            raise HTTPException(400, f"Status-Wechsel von '{inv.status}' nach 'overdue' nicht erlaubt.")
        inv.status = "overdue"
        db.flush()
        db.refresh(inv)
        return inv


@router.delete("/invoices/{invoice_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_finance_invoice(
    request: Request,
    invoice_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        inv = db.query(FinanceInvoice).filter(FinanceInvoice.id == invoice_id, FinanceInvoice.user_id == uid).first()
        if not inv:
            raise HTTPException(404, "Rechnung nicht gefunden.")
        db.delete(inv)
