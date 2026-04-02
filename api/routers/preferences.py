"""User Preferences Router – Nav-Config, Dashboard-Widgets, Appearance."""

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user
from api.schemas.preferences import PreferencesUpdateSchema
from src.services.preferences_service import (
    get_preferences,
    update_preferences,
    get_nav_registry,
    get_dashboard_widget_registry,
)

router = APIRouter()


@router.get("")
async def read_preferences(user_key: str = Depends(get_current_user)):
    """Gibt die aktuellen User-Preferences zurueck (mit Defaults gemergt)."""
    return get_preferences(user_key)


@router.patch("")
async def patch_preferences(
    body: PreferencesUpdateSchema,
    user_key: str = Depends(get_current_user),
):
    """Aktualisiert User-Preferences (partial update)."""
    try:
        return update_preferences(user_key, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/registry")
async def read_registry(user_key: str = Depends(get_current_user)):
    """Gibt die verfuegbaren Nav-Items und Dashboard-Widgets zurueck."""
    return {
        "nav_items": get_nav_registry(),
        "dashboard_widgets": get_dashboard_widget_registry(),
    }
