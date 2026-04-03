from pydantic import BaseModel


class ChatSuggestionOut(BaseModel):
    label: str
    message: str
    icon: str = "lightbulb"
    priority: int = 0


class ProactiveSuggestionOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    action_route: str = ""
    action_label: str = ""
    dismissible: bool = True
