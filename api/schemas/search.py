from pydantic import BaseModel
from typing import Optional


class SearchResult(BaseModel):
    type: str
    id: Optional[int] = None
    title: str
    subtitle: str = ""
    route: str = ""
