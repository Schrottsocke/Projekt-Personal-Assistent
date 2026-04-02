"""Pydantic-Schemas fuer User Preferences API."""

from pydantic import BaseModel


class NavItemSchema(BaseModel):
    id: str
    enabled: bool = True
    pinned: bool = False
    order: int = 0


class NavConfigSchema(BaseModel):
    items: list[NavItemSchema] | None = None


class DashboardWidgetSchema(BaseModel):
    id: str
    enabled: bool = True
    order: int = 0


class DashboardConfigSchema(BaseModel):
    widgets: list[DashboardWidgetSchema] | None = None


class AppearanceSchema(BaseModel):
    theme: str | None = None


class PreferencesUpdateSchema(BaseModel):
    nav: NavConfigSchema | None = None
    dashboard: DashboardConfigSchema | None = None
    appearance: AppearanceSchema | None = None
