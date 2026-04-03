from typing import Literal, Optional
from pydantic import BaseModel, Field


# V1 Trigger- und Action-Typen
TriggerType = Literal[
    "task_due_today",
    "event_tomorrow",
    "task_completed",
    "shopping_list_empty",
    "daily_time",
]

ActionType = Literal[
    "create_notification",
    "create_task",
    "add_shopping_items",
    "create_reminder",
]


class AutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    trigger_type: TriggerType
    trigger_config: dict = Field(default_factory=dict)
    action_type: ActionType
    action_config: dict = Field(default_factory=dict)
    description: str = Field("", max_length=1000)


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[dict] = None
    action_type: Optional[ActionType] = None
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
    last_triggered_at: Optional[str] = None
    created_at: str


class ConfigFieldInfo(BaseModel):
    key: str
    label: str
    type: str = "text"
    placeholder: str = ""
    required: bool = False
    options: Optional[list[dict]] = None


class TriggerInfo(BaseModel):
    id: str
    label: str
    icon: str
    description: str
    config_fields: list[ConfigFieldInfo] = []


class ActionInfo(BaseModel):
    id: str
    label: str
    icon: str
    description: str
    config_fields: list[ConfigFieldInfo] = []


class AutomationMeta(BaseModel):
    triggers: list[TriggerInfo]
    actions: list[ActionInfo]


class EvaluationResult(BaseModel):
    evaluated: int
    triggered: int
    details: list[dict]
