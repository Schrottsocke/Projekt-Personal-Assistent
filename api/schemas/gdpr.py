"""Pydantic-Schemas fuer GDPR/DSGVO-Endpunkte."""

from typing import Any

from pydantic import BaseModel


class GdprHealthResponse(BaseModel):
    status: str = "ok"
    module: str = "gdpr"


class DataExportResponse(BaseModel):
    user_key: str
    user_id: int
    data: dict[str, list[dict[str, Any]]] = {}


class DeleteAccountResponse(BaseModel):
    deleted: bool = True
    user_key: str
    counts: dict[str, int] = {}


class DeleteCategoryResponse(BaseModel):
    category: str
    deleted: bool = True
    counts: dict[str, int] = {}


class ConsentsResponse(BaseModel):
    user_key: str
    consents: dict[str, Any] = {}


class ConsentUpdateResponse(BaseModel):
    feature: str
    consented: bool
