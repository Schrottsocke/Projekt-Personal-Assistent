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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Contract ---


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    amount: float
    interval: Literal["monthly", "yearly", "quarterly"] = "monthly"
    start_date: date
    cancellation_deadline: Optional[date] = None
    next_billing: Optional[date] = None
    status: Literal["active", "cancelled", "expired"] = "active"


class ContractOut(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    interval: str
    start_date: date
    cancellation_deadline: Optional[date]
    next_billing: Optional[date]
    status: str
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
    amount: Optional[float] = None
    interval: Optional[Literal["monthly", "yearly", "quarterly"]] = None
    start_date: Optional[date] = None
    cancellation_deadline: Optional[date] = None
    next_billing: Optional[date] = None
    status: Optional[Literal["active", "cancelled", "expired"]] = None


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
    recipient: str = Field(..., min_length=1, max_length=200)
    total: float
    due_date: date
    status: Literal["open", "paid", "overdue"] = "open"
    pdf_path: Optional[str] = Field(None, max_length=500)


class FinanceInvoiceOut(BaseModel):
    id: int
    user_id: int
    recipient: str
    total: float
    due_date: date
    status: str
    pdf_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FinanceInvoice Update ---


class FinanceInvoiceUpdate(BaseModel):
    status: Optional[Literal["open", "paid", "overdue"]] = None
    pdf_path: Optional[str] = Field(None, max_length=500)
