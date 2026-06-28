from pydantic import BaseModel
from typing import Optional


class Place(BaseModel):
    name: str
    type: str                               # sightseeing | restaurant | activity
    lat: float
    lon: float
    why: str                                # why it matches user interest
    tip: Optional[str] = None              # practical visitor tip
    opening_hours: Optional[str] = None
    cuisine: Optional[str] = None
    walk_from_prev_min: Optional[int] = None


class WeatherSummary(BaseModel):
    date: str
    max_temp_c: float
    min_temp_c: float
    precipitation_mm: float
    condition: str


class CurrencyInfo(BaseModel):
    from_currency: str
    to_currency: str
    rate: float
    date: str


class CountryInfo(BaseModel):
    name: str
    capital: str
    currency: list[str]
    languages: list[str]
    timezones: list[str]
    flag: str


class ItineraryDay(BaseModel):
    day: int
    theme: str
    weather: Optional[WeatherSummary] = None
    places: list[Place]


class TravelPlan(BaseModel):
    destination: str
    total_days: int
    country_info: Optional[CountryInfo] = None
    currency_info: Optional[CurrencyInfo] = None
    days: list[ItineraryDay]
    intro: str
    bonus_tip: Optional[str] = None
