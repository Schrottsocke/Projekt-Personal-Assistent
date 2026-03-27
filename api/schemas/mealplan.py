from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MealPlanCreate(BaseModel):
    planned_date: str  # YYYY-MM-DD
    recipe_title: str
    recipe_chefkoch_id: Optional[str] = None
    recipe_image_url: Optional[str] = None
    meal_type: str = "dinner"  # breakfast|lunch|dinner
    servings: int = 4
    notes: Optional[str] = None


class MealPlanOut(MealPlanCreate):
    id: int
    user_key: str
    created_at: datetime

    class Config:
        from_attributes = True
