"""Pydantic-Schemas fuer Inventory-Produktlinie."""

from datetime import date, datetime
from typing import Optional

from pydantic import ConfigDict, BaseModel, Field


class InventoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    room: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = Field(None, max_length=500)
    value: Optional[float] = None
    purchase_date: Optional[date] = None
    receipt_doc_id: Optional[int] = None
    workspace_id: Optional[int] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    room: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = Field(None, max_length=500)
    value: Optional[float] = None
    purchase_date: Optional[date] = None
    receipt_doc_id: Optional[int] = None
    workspace_id: Optional[int] = None


class InventoryItemOut(BaseModel):
    id: int
    user_id: int
    workspace_id: Optional[int]
    name: str
    description: Optional[str]
    room: Optional[str]
    photo_url: Optional[str]
    value: Optional[float]
    purchase_date: Optional[date]
    receipt_doc_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValueSummary(BaseModel):
    total_value: float
    item_count: int


class WarrantyCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    purchase_date: Optional[date] = None
    warranty_end: Optional[date] = None
    vendor: Optional[str] = Field(None, max_length=200)
    receipt_doc_id: Optional[int] = None
    inventory_item_id: Optional[int] = None


class WarrantyUpdate(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    purchase_date: Optional[date] = None
    warranty_end: Optional[date] = None
    vendor: Optional[str] = Field(None, max_length=200)
    receipt_doc_id: Optional[int] = None
    inventory_item_id: Optional[int] = None


class WarrantyOut(BaseModel):
    id: int
    user_id: int
    product_name: str
    purchase_date: Optional[date]
    warranty_end: Optional[date]
    vendor: Optional[str]
    receipt_doc_id: Optional[int]
    inventory_item_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceiptLinkRequest(BaseModel):
    document_id: int


class RoomListOut(BaseModel):
    rooms: list[str]


class DocumentScanResult(BaseModel):
    document_id: int
    category: Optional[str]
    deadline: Optional[date]
    ocr_confidence: Optional[float]
    summary: Optional[str]
    suggested_action: str


class DocumentSearchResult(BaseModel):
    id: int
    doc_type: str
    filename: str
    summary: Optional[str]
    category: Optional[str]
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)
