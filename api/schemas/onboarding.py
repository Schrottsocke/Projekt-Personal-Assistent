"""Pydantic-Schemas fuer Onboarding-Flow."""

from typing import Literal, Optional

from pydantic import ConfigDict, BaseModel, Field


class OnboardingProfileStep(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    household_size: Literal["single", "couple", "family"] = "single"
    has_side_business: bool = False


class OnboardingProductLines(BaseModel):
    finance: bool = False
    inventory: bool = False
    family: bool = False


class OnboardingDashboard(BaseModel):
    widgets: list[str] = Field(..., min_length=0)


class OnboardingFirstAction(BaseModel):
    action: str = Field(..., max_length=50)


class OnboardingStatus(BaseModel):
    is_onboarded: bool
    current_step: int
    household_size: Optional[str] = None
    has_side_business: bool = False
    product_lines: dict[str, bool] = {}

    model_config = ConfigDict(from_attributes=True)
