from typing import Optional

from pydantic import BaseModel


class WeatherCurrent(BaseModel):
    location: str
    temp_c: float
    feels_like_c: float
    humidity: int
    wind_kmph: float
    description: str
    min_temp_c: float
    max_temp_c: float


class WeatherForecastDay(BaseModel):
    date: str
    min_temp_c: float
    max_temp_c: float
    description: str


class WeatherResponse(BaseModel):
    current: WeatherCurrent
    forecast: list[WeatherForecastDay] = []
    raw_text: Optional[str] = None
