"""Inventory-Router: InventoryItems, Warranties."""

from fastapi import APIRouter

from src.services.database import InventoryItem, Warranty  # noqa: F401

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "module": "inventory"}
