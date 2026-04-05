"""Onboarding-Router: Schritt-fuer-Schritt Einrichtung fuer neue Privatkunden."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.onboarding import (
    OnboardingDashboard,
    OnboardingFirstAction,
    OnboardingProductLines,
    OnboardingProfileStep,
    OnboardingStatus,
)
from config.settings import settings
from src.services.database import UserProfile, get_db

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _get_profile(db, user_key: str) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(404, "User-Profil nicht gefunden.")
    return profile


def _get_onboarding(profile: UserProfile) -> dict:
    """Liest onboarding-State aus preferences_json."""
    if profile.preferences_json:
        try:
            prefs = json.loads(profile.preferences_json)
            return prefs.get("onboarding", {})
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _set_onboarding(profile: UserProfile, onboarding: dict) -> None:
    """Schreibt onboarding-State in preferences_json."""
    prefs = {}
    if profile.preferences_json:
        try:
            prefs = json.loads(profile.preferences_json)
        except (json.JSONDecodeError, TypeError):
            prefs = {}
    prefs["onboarding"] = onboarding
    profile.preferences_json = json.dumps(prefs)


def _get_enabled_features(profile: UserProfile) -> dict:
    if profile.enabled_features:
        try:
            return json.loads(profile.enabled_features)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


@router.get("/health")
async def health():
    return {"status": "ok", "module": "onboarding"}


@router.get("/status", response_model=OnboardingStatus)
async def get_status(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        ob = _get_onboarding(profile)
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=profile.is_onboarded or False,
            current_step=ob.get("current_step", 0),
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/profile", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def set_profile(
    request: Request,
    body: OnboardingProfileStep,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        profile.nickname = body.name
        ob = _get_onboarding(profile)
        ob["household_size"] = body.household_size
        ob["has_side_business"] = body.has_side_business
        ob["current_step"] = max(ob.get("current_step", 0), 1)
        _set_onboarding(profile, ob)
        db.flush()
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=profile.is_onboarded or False,
            current_step=ob["current_step"],
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/product-lines", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def set_product_lines(
    request: Request,
    body: OnboardingProductLines,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        features = _get_enabled_features(profile)
        features["finance"] = body.finance
        features["inventory"] = body.inventory
        features["family"] = body.family
        profile.enabled_features = json.dumps(features)
        ob = _get_onboarding(profile)
        ob["current_step"] = max(ob.get("current_step", 0), 2)
        _set_onboarding(profile, ob)
        db.flush()
        return OnboardingStatus(
            is_onboarded=profile.is_onboarded or False,
            current_step=ob["current_step"],
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/first-action", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def set_first_action(
    request: Request,
    body: OnboardingFirstAction,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        ob = _get_onboarding(profile)
        actions = ob.get("first_actions", [])
        if body.action not in actions:
            actions.append(body.action)
        ob["first_actions"] = actions
        ob["current_step"] = max(ob.get("current_step", 0), 3)
        _set_onboarding(profile, ob)
        db.flush()
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=profile.is_onboarded or False,
            current_step=ob["current_step"],
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/dashboard", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def set_dashboard(
    request: Request,
    body: OnboardingDashboard,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        prefs = {}
        if profile.preferences_json:
            try:
                prefs = json.loads(profile.preferences_json)
            except (json.JSONDecodeError, TypeError):
                prefs = {}
        widgets = []
        for i, wid in enumerate(body.widgets):
            widgets.append({"id": wid, "enabled": True, "order": i})
        prefs.setdefault("dashboard", {})["widgets"] = widgets
        ob = prefs.get("onboarding", {})
        ob["current_step"] = max(ob.get("current_step", 0), 4)
        prefs["onboarding"] = ob
        profile.preferences_json = json.dumps(prefs)
        db.flush()
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=profile.is_onboarded or False,
            current_step=ob["current_step"],
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/complete", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def complete_onboarding(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        profile.is_onboarded = True
        ob = _get_onboarding(profile)
        ob["current_step"] = 5
        _set_onboarding(profile, ob)
        db.flush()
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=True,
            current_step=5,
            household_size=ob.get("household_size"),
            has_side_business=ob.get("has_side_business", False),
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )


@router.post("/restart", response_model=OnboardingStatus, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def restart_onboarding(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = _get_profile(db, user_key)
        profile.is_onboarded = False
        _set_onboarding(profile, {"current_step": 0})
        db.flush()
        features = _get_enabled_features(profile)
        return OnboardingStatus(
            is_onboarded=False,
            current_step=0,
            product_lines={
                "finance": features.get("finance", False),
                "inventory": features.get("inventory", False),
                "family": features.get("family", False),
            },
        )
