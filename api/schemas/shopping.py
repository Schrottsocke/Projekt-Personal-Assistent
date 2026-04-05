import re
from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, Field, field_validator


def _validate_quantity(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if re.match(r"^-\d+(\.\d+)?$", v):
        raise ValueError("Menge darf nicht negativ sein.")
    return v


class ShoppingItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)

    _check_quantity = field_validator("quantity")(_validate_quantity)


class ShoppingItemOut(BaseModel):
    id: int
    name: str
    quantity: Optional[str]
    unit: Optional[str]
    category: Optional[str]
    checked: bool
    source: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShoppingItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    checked: Optional[bool] = None
    quantity: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)

    _check_quantity = field_validator("quantity")(_validate_quantity)
