import os
from functools import lru_cache

import httpx

USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "TravelAgent/1.0")


@lru_cache(maxsize=128)
def geocode_city(city: str) -> dict:
    """Convert a city name to latitude and longitude coordinates.

    Args:
        city: City name e.g. 'New York', 'Paris', 'Tokyo'

    Returns:
        dict with lat, lon, display_name on success; status='error' on failure.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params=params, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            results = r.json()
        if not results:
            return {"status": "error", "message": f"City not found: {city}"}
        return {
            "status": "ok",
            "city": city,
            "lat": float(results[0]["lat"]),
            "lon": float(results[0]["lon"]),
            "display_name": results[0].get("display_name", city),
        }
    except Exception as exc:
        return {"status": "error", "message": f"Geocode error: {exc}"}
