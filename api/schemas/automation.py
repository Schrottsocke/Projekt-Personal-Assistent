from typing import Literal, Optional
from pydantic import BaseModel, Field


class AutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_type: Literal["schedule", "event", "condition"]
    trigger_config: dict = Field(default_factory=dict)
    action_type: Literal["notification", "task", "email", "inbox"]
    action_config: dict = Field(default_factory=dict)
    description: str = Field("", max_length=1000)


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    trigger_config: Optional[dict] = None
    action_config: Optional[dict] = None
    description: Optional[str] = Field(None, max_length=1000)
    active: Optional[bool] = None


class AutomationRuleOut(BaseModel):
    id: str
    name: str
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    description: str
    active: bool
    trigger_count: int
    created_at: str
