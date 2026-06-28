import os
import time
import json
import urllib.request
import urllib.parse
from src.tools.geocode_tool import geocode_city

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
_UA = "TravelAgent/1.0 (educational project; contact: traveler@example.com)"

INTEREST_TAG_MAP: dict[str, list[str]] = {
    "historical": ['["historic"]', '["tourism"="museum"]'],
    "history":    ['["historic"]', '["tourism"="museum"]'],
    "museum":     ['["tourism"="museum"]'],
    "art":        ['["tourism"="gallery"]', '["amenity"="arts_centre"]'],
    "nature":     ['["leisure"="park"]', '["natural"="peak"]', '["leisure"="garden"]'],
    "park":       ['["leisure"="park"]'],
    "restaurant": ['["amenity"="restaurant"]'],
    "food":       ['["amenity"="restaurant"]', '["amenity"="cafe"]'],
    "cafe":       ['["amenity"="cafe"]'],
    "shopping":   ['["shop"="mall"]', '["shop"="department_store"]'],
    "nightlife":  ['["amenity"="bar"]', '["amenity"="nightclub"]'],
}


def _overpass_query(tag_filter: str, lat: float, lon: float,
                    radius: int, limit: int) -> list[dict]:
    query = (
        f'[out:json][timeout:25];\n'
        f'nwr{tag_filter}(around:{radius},{lat},{lon});\n'
        f'out center {limit};'
    )
    data = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                OVERPASS_URL, data=data, method="POST",
                headers={"User-Agent": _UA},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode()).get("elements", [])
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
    return []


def get_places(city: str, interest: str, limit: int = 8) -> dict:
    """Find points of interest in a city filtered by interest type.

    Args:
        city: Destination city name.
        interest: Type of interest — one of: historical, art, nature, park,
                  museum, shopping, nightlife.
        limit: Max number of places to return (default 8).

    Returns:
        dict with a 'places' list. Each place has name, lat, lon, type,
        address, and opening_hours. status='error' on failure.
    """
    geo = geocode_city(city)
    if geo["status"] != "ok":
        return geo

    tag_filters = INTEREST_TAG_MAP.get(interest.lower(), ['["tourism"]'])
    seen: set[str] = set()
    results: list[dict] = []

    for tag_filter in tag_filters:
        if len(results) >= limit:
            break
        elements = _overpass_query(tag_filter, geo["lat"], geo["lon"],
                                   radius=5000, limit=limit)
        for e in elements:
            name = e.get("tags", {}).get("name", "")
            if not name or name in seen:
                continue
            lat = e.get("lat") or e.get("center", {}).get("lat")
            lon = e.get("lon") or e.get("center", {}).get("lon")
            if not lat or not lon:
                continue
            seen.add(name)
            results.append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "type": interest,
                "address": e["tags"].get("addr:street", ""),
                "opening_hours": e["tags"].get("opening_hours", ""),
            })

    return {"status": "ok", "city": city, "interest": interest, "places": results[:limit]}


def get_restaurants(city: str, cuisine: str = "", limit: int = 8) -> dict:
    """Find restaurants in a city, optionally filtered by cuisine.

    Args:
        city: Destination city name.
        cuisine: Cuisine type e.g. 'italian', 'japanese', 'indian' (optional).
        limit: Max number of restaurants to return (default 8).

    Returns:
        dict with a 'places' list. Each entry has name, lat, lon, cuisine,
        address, and opening_hours. status='error' on failure.
    """
    geo = geocode_city(city)
    if geo["status"] != "ok":
        return geo

    elements = _overpass_query('["amenity"="restaurant"]', geo["lat"], geo["lon"],
                               radius=5000, limit=limit * 3)

    results: list[dict] = []
    seen: set[str] = set()
    for e in elements:
        name = e.get("tags", {}).get("name", "")
        if not name or name in seen:
            continue
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if not lat or not lon:
            continue
        ecuisine = e["tags"].get("cuisine", "")
        if cuisine and cuisine.lower() not in ecuisine.lower():
            continue
        seen.add(name)
        results.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "type": "restaurant",
            "cuisine": ecuisine,
            "address": e["tags"].get("addr:street", ""),
            "opening_hours": e["tags"].get("opening_hours", ""),
        })
        if len(results) >= limit:
            break

    return {"status": "ok", "city": city, "cuisine": cuisine, "places": results}
