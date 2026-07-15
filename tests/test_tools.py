"""Integration tests — hit real APIs (all free, no keys required)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools import (
    geocode_city, get_weather, get_places, get_restaurants,
    get_currency_rate, get_country_info, get_route_time,
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


def test_weather():
    r = get_weather("London", days=3)
    assert r["status"] == "ok"
    assert len(r["daily"]) == 3
    assert "max_temp_c" in r["daily"][0]


def test_places_historical():
    r = get_places("Paris", "historical", limit=5)
    assert r["status"] == "ok"
    assert len(r["places"]) > 0
    assert "name" in r["places"][0]
    assert "lat" in r["places"][0]


def test_restaurants():
    r = get_restaurants("Tokyo", cuisine="ramen", limit=5)
    assert r["status"] == "ok"


def test_currency():
    r = get_currency_rate("USD", "EUR")
    assert r["status"] == "ok"
    assert 0.5 < r["rate"] < 2.0


def test_currency_jpy():
    r = get_currency_rate("USD", "JPY")
    assert r["status"] == "ok"
    assert r["rate"] > 100


def test_country_info():
    r = get_country_info("France")
    assert r["status"] == "ok"
    assert r["capital"] == "Paris"
    assert "EUR" in r["currency"]


def test_routing():
    # Empire State Building → Times Square
    r = get_route_time(40.7484, -73.9967, 40.7580, -73.9855, mode="walking")
    assert r["status"] == "ok"
    assert r["duration_min"] > 0
    assert r["distance_km"] > 0


if __name__ == "__main__":
    tests = [
        test_geocode, test_geocode_cache, test_geocode_unknown,
        test_weather, test_places_historical, test_restaurants,
        test_currency, test_currency_jpy, test_country_info, test_routing,
    ]
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
