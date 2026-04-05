"""Pydantic-Schemas fuer Finance-Produktlinie (Transactions, Contracts, Budgets)."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import ConfigDict, BaseModel, Field


# --- Transaction ---


class TransactionCreate(BaseModel):
    date: datetime
    amount: float
    currency: str = Field("EUR", max_length=10)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    source: Literal["csv", "manual", "scan"] = "manual"
    raw_text: Optional[str] = None
    contract_id: Optional[int] = None


class TransactionOut(BaseModel):
    id: int
    user_id: int
    date: datetime
    amount: float
    currency: str
    category: Optional[str]
    description: Optional[str]
    source: str
    raw_text: Optional[str]
    contract_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CsvImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    total_rows: int


# --- Contract ---


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    provider: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    amount: float
    interval: Literal["monthly", "yearly", "quarterly"] = "monthly"
    start_date: date
    end_date: Optional[date] = None
    cancellation_days: Optional[int] = None
    cancellation_deadline: Optional[date] = None
    next_billing: Optional[date] = None
    status: Literal["active", "cancelled", "expired"] = "active"
    notes: Optional[str] = None


class ContractOut(BaseModel):
    id: int
    user_id: int
    name: str
    provider: Optional[str] = None
    category: Optional[str] = None
    amount: float
    interval: str
    start_date: date
    end_date: Optional[date] = None
    cancellation_days: Optional[int] = None
    cancellation_deadline: Optional[date] = None
    next_billing: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Budget ---


class BudgetCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    monthly_limit: float = Field(..., gt=0)
    alert_threshold: Optional[float] = Field(None, ge=0, le=100)


class BudgetOut(BaseModel):
    id: int
    user_id: int
    category: str
    monthly_limit: float
    alert_threshold: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Contract Update ---


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    interval: Optional[Literal["monthly", "yearly", "quarterly"]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    cancellation_days: Optional[int] = None
    cancellation_deadline: Optional[date] = None
    next_billing: Optional[date] = None
    status: Optional[Literal["active", "cancelled", "expired"]] = None
    notes: Optional[str] = None


# --- Contract Summary ---


class ContractSummary(BaseModel):
    total_monthly_cost: float
    active_count: int
    expiring_soon: list[ContractOut]


# --- Budget Alert ---


class BudgetAlert(BaseModel):
    category: str
    monthly_limit: float
    spent: float
    percentage: float
    over_limit: bool


# --- Monthly Overview ---


class MonthlyOverview(BaseModel):
    year: int
    month: int
    total_income: float
    total_expenses: float
    by_category: dict[str, float]


# --- FinanceInvoice ---


class FinanceInvoiceCreate(BaseModel):
    invoice_number: Optional[str] = Field(None, max_length=50)
    recipient: str = Field(..., min_length=1, max_length=200)
    recipient_address: Optional[str] = None
    issue_date: Optional[date] = None
    total: float
    tax_rate: Optional[float] = None
    due_date: date
    status: Literal["open", "paid", "overdue", "draft"] = "open"
    pdf_path: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class FinanceInvoiceOut(BaseModel):
    id: int
    user_id: int
    invoice_number: Optional[str] = None
    recipient: str
    recipient_address: Optional[str] = None
    issue_date: Optional[date] = None
    total: float
    tax_rate: Optional[float] = None
    due_date: date
    status: str
    payment_date: Optional[date] = None
    pdf_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinanceInvoiceUpdate(BaseModel):
    recipient: Optional[str] = None
    recipient_address: Optional[str] = None
    total: Optional[float] = None
    tax_rate: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[Literal["open", "paid", "overdue", "draft"]] = None
    payment_date: Optional[date] = None
    pdf_path: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
