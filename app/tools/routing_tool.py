import os
import httpx

OSRM_URL = os.getenv("OSRM_URL", "http://router.project-osrm.org")


def get_route_time(lat1: float, lon1: float,
                   lat2: float, lon2: float,
                   mode: str = "walking") -> dict:
    """Get travel time and distance between two coordinates.

    Use this tool to calculate walking or driving time between stops on a
    daily itinerary, helping order them by proximity.

    Args:
        lat1: Latitude of the starting point.
        lon1: Longitude of the starting point.
        lat2: Latitude of the destination.
        lon2: Longitude of the destination.
        mode: 'walking' (default) or 'driving'.

    Returns:
        dict with distance_km, duration_min, and mode.
        status='error' on failure.
    """
    profile = "foot" if mode == "walking" else "driving"
    url = f"{OSRM_URL}/route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}"
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params={"overview": "false"})
            r.raise_for_status()
            route = r.json()["routes"][0]
        return {
            "status": "ok",
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60, 1),
            "mode": mode,
        }
    except Exception as exc:
        return {"status": "error", "message": f"Routing API error: {exc}"}
