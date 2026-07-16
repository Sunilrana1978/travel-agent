"""Integration tests — hit real APIs (all free, no keys required)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools import (
    geocode_city,
    get_country_info,
    get_currency_rate,
    get_places,
    get_restaurants,
    get_route_time,
    get_weather,
)


def test_geocode():
    r = geocode_city("New York")
    assert r["status"] == "ok"
    assert 40 < r["lat"] < 41
    assert -75 < r["lon"] < -73


def test_geocode_cache():
    r1 = geocode_city("Paris")
    r2 = geocode_city("Paris")
    assert r1 == r2  # lru_cache hit


def test_geocode_unknown():
    r = geocode_city("XxXNotACityXxX")
    assert r["status"] == "error"


async def test_weather():
    r = await get_weather("London", days=3)
    assert r["status"] == "ok"
    assert len(r["daily"]) == 3
    assert "max_temp_c" in r["daily"][0]


async def test_places_historical():
    r = await get_places("Paris", "historical", limit=5)
    assert r["status"] == "ok"
    assert len(r["places"]) > 0
    assert "name" in r["places"][0]
    assert "lat" in r["places"][0]


async def test_restaurants():
    r = await get_restaurants("Tokyo", cuisine="ramen", limit=5)
    assert r["status"] == "ok"


async def test_currency():
    r = await get_currency_rate("USD", "EUR")
    assert r["status"] == "ok"
    assert 0.5 < r["rate"] < 2.0


async def test_currency_jpy():
    r = await get_currency_rate("USD", "JPY")
    assert r["status"] == "ok"
    assert r["rate"] > 100


async def test_country_info():
    r = await get_country_info("France")
    assert r["status"] == "ok"
    assert r["capital"] == "Paris"
    assert "EUR" in r["currency"]


async def test_routing():
    # Empire State Building → Times Square
    r = await get_route_time(40.7484, -73.9967, 40.7580, -73.9855, mode="walking")
    assert r["status"] == "ok"
    assert r["duration_min"] > 0
    assert r["distance_km"] > 0


if __name__ == "__main__":
    tests = [
        test_geocode, test_geocode_cache, test_geocode_unknown,
        test_weather, test_places_historical, test_restaurants,
        test_currency, test_currency_jpy, test_country_info, test_routing,
    ]
    import inspect
    for t in tests:
        try:
            if inspect.iscoroutinefunction(t):
                asyncio.run(t())
            else:
                t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
