"""Pydantic-Schemas fuer Rechnungen."""

from typing import Optional

from pydantic import ConfigDict, BaseModel, Field


class InvoiceItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(1, gt=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: float = Field(0, ge=0, le=100)
    # Berechnet vom Backend:
    net_total: Optional[float] = None
    tax_amount: Optional[float] = None


class InvoiceCreate(BaseModel):
    invoice_type: str = Field("kleinunternehmer", pattern="^(kleinunternehmer|regelbesteuerung)$")
    invoice_number: Optional[str] = None
    status: str = Field("draft", pattern="^(draft|sent|paid|cancelled)$")
    # Absender
    sender_name: str = Field("", max_length=200)
    sender_address: str = Field("", max_length=500)
    sender_tax_id: str = Field("", max_length=50)
    sender_vat_id: str = Field("", max_length=50)
    sender_bank: str = Field("", max_length=300)
    # Empfaenger
    recipient_name: str = Field("", max_length=200)
    recipient_address: str = Field("", max_length=500)
    # Daten
    invoice_date: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_period: Optional[str] = None
    payment_terms: str = Field("14 Tage netto", max_length=200)
    # Positionen
    items: list[InvoiceItem] = Field(default_factory=list)
    notes: str = Field("", max_length=2000)


class InvoiceUpdate(BaseModel):
    invoice_type: Optional[str] = Field(None, pattern="^(kleinunternehmer|regelbesteuerung)$")
    invoice_number: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|sent|paid|cancelled)$")
    sender_name: Optional[str] = Field(None, max_length=200)
    sender_address: Optional[str] = Field(None, max_length=500)
    sender_tax_id: Optional[str] = Field(None, max_length=50)
    sender_vat_id: Optional[str] = Field(None, max_length=50)
    sender_bank: Optional[str] = Field(None, max_length=300)
    recipient_name: Optional[str] = Field(None, max_length=200)
    recipient_address: Optional[str] = Field(None, max_length=500)
    invoice_date: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_period: Optional[str] = None
    payment_terms: Optional[str] = Field(None, max_length=200)
    items: Optional[list[InvoiceItem]] = None
    notes: Optional[str] = Field(None, max_length=2000)


class InvoiceOut(BaseModel):
    id: str
    invoice_number: str
    invoice_type: str
    status: str
    sender_name: str
    sender_address: str
    sender_tax_id: str
    sender_vat_id: str
    sender_bank: str
    recipient_name: str
    recipient_address: str
    invoice_date: str
    delivery_date: Optional[str] = None
    delivery_period: Optional[str] = None
    payment_terms: str
    items: list[InvoiceItem] = Field(default_factory=list)
    subtotal: float
    tax_total: float
    total: float
    notes: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)
