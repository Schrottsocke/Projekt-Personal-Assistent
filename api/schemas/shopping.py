from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ShoppingItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)


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
    quantity: Optional[str] = Field(None, max_length=50)
