from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field("", max_length=65536)
    labels: list[str] = Field(default_factory=list)


class IssueOut(BaseModel):
    number: int
    title: str
    html_url: str
    labels: list[str]
    created_at: str


class LabelOut(BaseModel):
    name: str
    color: str
    description: str | None = None
