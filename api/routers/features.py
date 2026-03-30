"""Features-Router: Feature-Marketplace für Flutter App."""

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user
from src.features.feature_service import get_feature_status_list, toggle_feature

router = APIRouter(prefix="/features", tags=["features"])


@router.get("")
async def list_features(user_key: str = Depends(get_current_user)):
    """Gibt alle Features mit aktiviertem/deaktiviertem Status zurück."""
    return get_feature_status_list(user_key)


@router.post("/{feature_id}/toggle")
async def toggle(feature_id: str, user_key: str = Depends(get_current_user)):
    """Schaltet ein Feature um. Gibt neuen Zustand zurück."""
    try:
        new_state = toggle_feature(user_key, feature_id)
        return {"feature_id": feature_id, "enabled": new_state}
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Feature nicht gefunden oder kann nicht umgeschaltet werden.")
