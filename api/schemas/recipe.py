from datetime import datetime
from typing import Optional
from pydantic import ConfigDict, BaseModel, Field


class RecipeSearchResult(BaseModel):
    chefkoch_id: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    image_url: Optional[str] = Field(None, max_length=500)
    prep_time: int = Field(0, ge=0)
    cook_time: int = Field(0, ge=0)
    difficulty: Optional[str] = Field(None, max_length=50)
    rating: float = Field(0.0, ge=0.0, le=5.0)
    url: str = Field(..., max_length=500)


class RecipeFull(RecipeSearchResult):
    servings: int = Field(4, ge=1)
    ingredients: list[dict] = []
    instructions: Optional[str] = Field(None, max_length=10000)


class SavedRecipeCreate(BaseModel):
    chefkoch_id: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    image_url: Optional[str] = Field(None, max_length=500)
    servings: int = Field(4, ge=1)
    prep_time: int = Field(0, ge=0)
    cook_time: int = Field(0, ge=0)
    difficulty: Optional[str] = Field(None, max_length=50)
    ingredients_json: Optional[str] = Field(None, max_length=20000)
    source_url: Optional[str] = Field(None, max_length=500)


class SavedRecipeOut(SavedRecipeCreate):
    id: int
    user_key: str
    is_favorite: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToShoppingRequest(BaseModel):
    servings: int = Field(4, ge=1, le=100)  # Für Portionskalkulation


class IngredientItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    amount: Optional[str] = None
    unit: Optional[str] = None


class SelectedIngredientsRequest(BaseModel):
    ingredients: list[IngredientItem] = Field(..., min_length=1)
