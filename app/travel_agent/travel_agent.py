import asyncio

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.tools import (
    geocode_city,
    get_country_info,
    get_currency_rate,
    get_places,
    get_restaurants,
    get_route_time,
    get_weather,
)

load_dotenv()

SYSTEM_PROMPT = """You are an expert travel itinerary planner. You help users plan personalised day-by-day trips.

## How to handle a new trip request

1. **Geocode first**: Call `geocode_city` to get coordinates.
2. **Gather context and places in parallel**: In a single response, emit tool calls in parallel for:
   - `get_weather` (days = trip length)
   - `get_country_info` (country of destination)
   - `get_currency_rate` (user's home currency → destination currency; default USD if not specified)
   - `get_places` (for each interest/theme the user mentioned, e.g. Call once for historical, once for nature, etc.)
   - `get_restaurants` (if the user mentioned food/dining or restaurants)
3. **Order stops and query routing in parallel**: Arrange the places into logical, geographically structured days. In a single response, emit multiple `get_route_time` tool calls in parallel to calculate walking times between all consecutive stops.
4. **Build the itinerary**: Produce 3–4 stops per day, themed by interest.
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
  "bonus_tip": "Best local tip for the destination.",
  "budget_estimate": {
    "currency": "USD",
    "per_day_low": 50,
    "per_day_mid": 120,
    "per_day_high": 250,
    "notes": "Budget/mid-range/luxury estimate covering accommodation, food, and local transport."
  },
  "packing_list": ["Item based on weather and trip type", "e.g. Rain jacket", "Comfortable walking shoes"],
  "hotel_areas": [
    {
      "name": "Neighbourhood Name",
      "why": "Why it's the best base for this itinerary",
      "price_range": "$$"
    }
  ]
}
```

Guidelines for new fields:
- **budget_estimate**: Base on destination cost-of-living. Low = hostel/street food, Mid = 3-star hotel/casual restaurants, High = 4-5 star/fine dining. Use destination currency if user specified one.
- **packing_list**: 6–10 items tailored to the weather forecast and trip type (beach, hiking, city, etc.).
- **hotel_areas**: 2–3 neighbourhoods ordered by best location for the planned stops. `price_range` uses $ to $$$$.

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

from google.adk.tools.agent_tool import AgentTool

# ── Geographic Context Agent ─────────────────────────────────────────────────
geographic_agent = Agent(
    name="geographic_agent",
    model="gemini-2.5-flash",
    description="Geographic context specialist. Geocodes cities, fetches weather, country information, and exchange rates.",
    instruction="""You are a geographic context specialist. When given a destination city and duration:
    1. Geocode the city first using `geocode_city`.
    2. Get weather information using `get_weather` for the duration.
    3. Get country info using `get_country_info`.
    4. Get currency exchange rates using `get_currency_rate`.
    Respond with a structured summary containing coordinates, weather, country flags/languages, and currency details.""",
    tools=[geocode_city, get_weather, get_country_info, get_currency_rate],
)

# ── Points of Interest (POI) & Dining Agent ─────────────────────────────────
poi_agent = Agent(
    name="poi_agent",
    model="gemini-2.5-flash",
    description="Dining and points of interest specialist. Finds sightseeing places and restaurants based on user interests.",
    instruction="""You are a dining and activities specialist. Given a destination and user interests:
    1. Find points of interest using `get_places`.
    2. Find dining recommendations using `get_restaurants`.
    Respond with a list of sights and restaurants including locations, opening hours, and why they fit user goals.""",
    tools=[get_places, get_restaurants],
)

# ── Logistics & Routing Agent ────────────────────────────────────────────────
logistics_agent = Agent(
    name="logistics_agent",
    model="gemini-2.5-flash",
    description="Logistics and route optimization specialist. Orders stops geographically and calculates travel durations.",
    instruction="""You are a logistical routing optimizer. Given a list of places and coordinates:
    1. Group them logically day-by-day.
    2. Order stops geographically to minimize walking.
    3. Calculate walking durations between consecutive stops using `get_route_time`.
    Respond with the optimized itinerary days and travel times.""",
    tools=[get_route_time],
)

# Wrap sub-agents as tools
geographic_tool = AgentTool(agent=geographic_agent)
poi_tool = AgentTool(agent=poi_agent)
logistics_tool = AgentTool(agent=logistics_agent)

# Orchestrator prompt
SYSTEM_PROMPT_ORCHESTRATOR = """You are the Lead Travel Planning Orchestrator. You help users plan day-by-day trips by coordinating specialized sub-agents.

## Your Process

1. **Context Gathering**: Call `geographic_agent` with the destination and length of trip.
2. **POI & Dining Selection**: Call `poi_agent` with the destination and user's interests.
3. **Route & Day Optimization**: Send the gathered details to `logistics_agent` to compile, group, and route them day-by-day.
4. **Itinerary Generation**: Combine all information and respond with a JSON matching this schema exactly:
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
  "bonus_tip": "Best local tip for the destination.",
  "budget_estimate": {
    "currency": "USD",
    "per_day_low": 50,
    "per_day_mid": 120,
    "per_day_high": 250,
    "notes": "Budget/mid-range/luxury estimate covering accommodation, food, and local transport."
  },
  "packing_list": ["Item based on weather and trip type", "e.g. Rain jacket", "Comfortable walking shoes"],
  "hotel_areas": [
    {
      "name": "Neighbourhood Name",
      "why": "Why it's the best base for this itinerary",
      "price_range": "$$"
    }
  ]
}
```

Guidelines for new fields:
- **budget_estimate**: Base on destination cost-of-living. Low = hostel/street food, Mid = 3-star hotel/casual restaurants, High = 4-5 star/fine dining. Use destination currency if user specified one.
- **packing_list**: 6–10 items tailored to the weather forecast and trip type (beach, hiking, city, etc.).
- **hotel_areas**: 2–3 neighbourhoods ordered by best location for the planned stops. `price_range` uses $ to $$$$.

Return ONLY the JSON — no markdown fences, no explanation text around it.

## Multi-turn conversations

For follow-up questions (e.g. "add more restaurants to Day 2", "what's the weather on Day 3"):
- Use the conversation history — do not re-geocode unless the city changed.
- Answer naturally and update the relevant part of the plan.
- For simple follow-ups you may respond in plain text without JSON.
"""

root_agent = _agent = Agent(
    name=_APP_NAME,
    model="gemini-2.5-flash",
    description="Expert travel itinerary planner that creates day-by-day trips.",
    instruction=SYSTEM_PROMPT_ORCHESTRATOR,
    tools=[geographic_tool, poi_tool, logistics_tool],
)

# App object — used by app/agent.py and app/fast_api_app.py
app = App(name=_APP_NAME, root_agent=root_agent)

_memory_service = InMemoryMemoryService()

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
    memory_service=_memory_service,
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
        except ServerError:
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
            else:
                raise
    return ""  # unreachable
