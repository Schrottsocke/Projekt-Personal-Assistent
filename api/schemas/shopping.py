from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ShoppingItemCreate(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class ShoppingItemOut(BaseModel):
    id: int
    name: str
    quantity: Optional[str]
    unit: Optional[str]
    category: Optional[str]
    checked: bool
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ShoppingItemUpdate(BaseModel):
    checked: Optional[bool] = None
    quantity: Optional[str] = None
