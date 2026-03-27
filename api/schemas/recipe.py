from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RecipeSearchResult(BaseModel):
    chefkoch_id: str
    title: str
    image_url: Optional[str] = None
    prep_time: int = 0
    cook_time: int = 0
    difficulty: Optional[str] = None
    rating: float = 0.0
    url: str


class RecipeFull(RecipeSearchResult):
    servings: int = 4
    ingredients: list[dict] = []
    instructions: Optional[str] = None


class SavedRecipeCreate(BaseModel):
    chefkoch_id: str
    title: str
    image_url: Optional[str] = None
    servings: int = 4
    prep_time: int = 0
    cook_time: int = 0
    difficulty: Optional[str] = None
    ingredients_json: Optional[str] = None
    source_url: Optional[str] = None


class SavedRecipeOut(SavedRecipeCreate):
    id: int
    user_key: str
    is_favorite: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ToShoppingRequest(BaseModel):
    servings: int = 4  # Für Portionskalkulation
