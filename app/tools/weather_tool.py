import httpx
from app.tools.geocode_tool import geocode_city

WMO_CONDITIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm",
}


def get_weather(city: str, days: int = 7) -> dict:
    """Get a daily weather forecast for a city.

    Args:
        city: Destination city name.
        days: Number of forecast days (1–16, default 7).

    Returns:
        dict with a 'daily' list, each entry having date, max/min temp,
        precipitation_mm, and condition string. status='error' on failure.
    """
    geo = geocode_city(city)
    if geo["status"] != "ok":
        return geo

    days = max(1, min(days, 16))
    params = {
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "forecast_days": days,
        "timezone": "auto",
    }
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get("https://api.open-meteo.com/v1/forecast", params=params)
            r.raise_for_status()
            d = r.json()["daily"]

        forecast = [
            {
                "date": d["time"][i],
                "max_temp_c": d["temperature_2m_max"][i],
                "min_temp_c": d["temperature_2m_min"][i],
                "precipitation_mm": d["precipitation_sum"][i],
                "condition": WMO_CONDITIONS.get(d["weathercode"][i], "Unknown"),
            }
            for i in range(len(d["time"]))
        ]
        return {"status": "ok", "city": city, "daily": forecast}
    except Exception as exc:
        return {"status": "error", "message": f"Weather API error: {exc}"}
