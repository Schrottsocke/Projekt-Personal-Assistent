"""Schemas fuer Household Documents (Upload, Response, Liste)."""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class HouseholdDocumentCreate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None  # invoice, warranty, insurance, receipt, contract, other
    run_ocr: bool = True


class HouseholdDocumentOut(BaseModel):
    id: int
    title: str
    category: Optional[str] = None
    file_path: Optional[str] = None
    ocr_text: Optional[str] = None
    deadline_date: Optional[date] = None
    issuer: Optional[str] = None
    amount: Optional[float] = None
    linked_inventory_item_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HouseholdDocumentList(BaseModel):
    items: list[HouseholdDocumentOut]
    total: int
