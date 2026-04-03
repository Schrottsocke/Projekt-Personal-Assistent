from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TravelTimeRequest(BaseModel):
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    profile: str = Field("auto", description="auto, fahrrad, laufen")


class TravelTimeResponse(BaseModel):
    origin: str
    destination: str
    duration_minutes: float
    distance_km: float
    profile: str
    summary: str


class DepartureTimeRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    arrival_time: datetime
    profile: str = "auto"
    buffer_minutes: int = Field(15, ge=0, le=120)


class DepartureTimeResponse(BaseModel):
    destination: str
    arrival_time: datetime
    recommended_departure: datetime
    travel_minutes: float
    buffer_minutes: int
    summary: str


class DailyFlowEntry(BaseModel):
    time: str
    type: str  # "event", "departure", "weather_warning"
    title: str
    detail: Optional[str] = None
    icon: Optional[str] = None


class DailyFlowResponse(BaseModel):
    date: str
    entries: list[DailyFlowEntry] = []
    weather_summary: Optional[str] = None
