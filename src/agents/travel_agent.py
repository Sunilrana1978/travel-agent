import asyncio

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.tools import (
    geocode_city, get_weather, get_places, get_restaurants,
    get_currency_rate, get_country_info, get_route_time,
)

load_dotenv()

SYSTEM_PROMPT = """You are an expert travel itinerary planner. You help users plan personalised day-by-day trips.

## How to handle a new trip request

1. **Geocode first**: Call `geocode_city` to get coordinates.
2. **Gather context in parallel**: In a single response emit tool_use blocks for:
   - `get_weather` (days = trip length)
   - `get_country_info` (country of destination)
   - `get_currency_rate` (user's home currency → destination currency; default USD if not specified)
3. **Gather places**: Call `get_places` for each interest the user mentioned.
   If the user mentioned food/dining, call `get_restaurants` too.
4. **Order stops**: Use `get_route_time` to calculate walking times between consecutive stops
   so each day flows geographically.
5. **Build the itinerary**: Produce 3–4 stops per day, themed by interest.
   Each Place must include a `why` (why it matches the user's interest) and a practical `tip`.

## Response format

After all tool calls are complete, respond with a JSON object matching this schema exactly:
```json
{
  "destination": "City, Country",
  "total_days": 3,
  "country_info": { "name": "...", "capital": "...", "currency": ["USD"], "languages": ["English"], "timezones": ["UTC-5"], "flag": "🇺🇸" },
  "currency_info": { "from_currency": "USD", "to_currency": "USD", "rate": 1.0, "date": "2024-01-01" },
  "days": [
    {
      "day": 1,
      "theme": "Historical Downtown",
      "weather": { "date": "2024-01-01", "max_temp_c": 20, "min_temp_c": 12, "precipitation_mm": 0, "condition": "Clear sky" },
      "places": [
        {
          "name": "Place Name",
          "type": "sightseeing",
          "lat": 40.7, "lon": -74.0,
          "why": "Perfect for history lovers — ...",
          "tip": "Arrive early to avoid queues.",
          "opening_hours": "9am–5pm",
          "cuisine": null,
          "walk_from_prev_min": null
        }
      ]
    }
  ],
  "intro": "Welcome to ... Here's your personalised itinerary!",
  "bonus_tip": "Best local tip for the destination."
}
```

Return ONLY the JSON — no markdown fences, no explanation text around it.

## Multi-turn conversations

For follow-up questions (e.g. "add more restaurants to Day 2", "what's the weather on Day 3"):
- Use the conversation history — do not re-geocode unless the city changed.
- Answer naturally and update the relevant part of the plan.
- For simple follow-ups you may respond in plain text without JSON.
"""

_APP_NAME = "travel_agent"
_USER_ID = "user"

_session_service = InMemorySessionService()

root_agent = _agent = Agent(
    name=_APP_NAME,
    model="gemini-2.5-flash",
    description="Expert travel itinerary planner that creates personalised day-by-day trips.",
    instruction=SYSTEM_PROMPT,
    tools=[
        geocode_city,
        get_weather,
        get_places,
        get_restaurants,
        get_currency_rate,
        get_country_info,
        get_route_time,
    ],
)

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


async def _run_async(user_message: str, session_id: str) -> str:
    session = await _session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
        )

    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    final_text = ""
    async for event in _runner.run_async(
        user_id=_USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    return final_text


def run_agent(user_message: str, session_id: str) -> str:
    """Run the travel agent for one user turn. Returns the assistant's response text."""
    import time
    from google.genai.errors import ServerError

    for attempt in range(3):
        try:
            return asyncio.run(_run_async(user_message, session_id))
        except ServerError as e:
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
            else:
                raise
    return ""  # unreachable
