import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from dotenv import load_dotenv

from src.tools import (
    geocode_city, get_weather, get_places, get_restaurants,
    get_currency_rate, get_country_info, get_route_time,
)

load_dotenv()

TOOL_FUNCTIONS = {
    "geocode_city":     geocode_city,
    "get_weather":      get_weather,
    "get_places":       get_places,
    "get_restaurants":  get_restaurants,
    "get_currency_rate": get_currency_rate,
    "get_country_info": get_country_info,
    "get_route_time":   get_route_time,
}

TOOLS = [
    {
        "name": "geocode_city",
        "description": "Convert a city name to latitude and longitude. Always call this first before any other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name e.g. 'New York', 'Paris'"}
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get a daily weather forecast for a city for the next N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "days": {"type": "integer", "description": "Number of days, 1–16. Match the user's trip length."},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_places",
        "description": "Find points of interest (attractions, museums, parks) in a city filtered by interest type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "interest": {
                    "type": "string",
                    "enum": ["historical", "history", "museum", "art", "nature", "park", "shopping", "nightlife"],
                    "description": "Category of attraction to search for.",
                },
                "limit": {"type": "integer", "description": "Max results (default 8)."},
            },
            "required": ["city", "interest"],
        },
    },
    {
        "name": "get_restaurants",
        "description": "Find restaurants in a city, optionally filtered by cuisine type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "cuisine": {
                    "type": "string",
                    "description": "Cuisine type e.g. 'italian', 'japanese', 'indian'. Leave empty for all.",
                },
                "limit": {"type": "integer", "description": "Max results (default 8)."},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_currency_rate",
        "description": "Get the live exchange rate between two currencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_currency": {"type": "string", "description": "Source ISO code e.g. 'USD'"},
                "to_currency":   {"type": "string", "description": "Target ISO code e.g. 'EUR', 'JPY'"},
            },
            "required": ["from_currency", "to_currency"],
        },
    },
    {
        "name": "get_country_info",
        "description": "Get destination country metadata: capital, currency, languages, timezone, flag.",
        "input_schema": {
            "type": "object",
            "properties": {
                "country_name": {"type": "string", "description": "Country name e.g. 'France', 'Japan'"},
            },
            "required": ["country_name"],
        },
    },
    {
        "name": "get_route_time",
        "description": "Get walking or driving time between two lat/lon points. Use to order daily stops by proximity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat1": {"type": "number"}, "lon1": {"type": "number"},
                "lat2": {"type": "number"}, "lon2": {"type": "number"},
                "mode": {"type": "string", "enum": ["walking", "driving"], "description": "Default: walking"},
            },
            "required": ["lat1", "lon1", "lat2", "lon2"],
        },
    },
]

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


def _execute_tool(block) -> dict:
    fn = TOOL_FUNCTIONS[block.name]
    try:
        result = fn(**block.input)
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}
    return {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": json.dumps(result),
    }


def run_agent(user_message: str, history: list[dict]) -> str:
    """Run the travel agent for one user turn. Returns the assistant's response text."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = history + [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_blocks = [b for b in response.content if b.type == "tool_use"]

            # Execute all tool calls in parallel using threads
            tool_results: list[dict] = [None] * len(tool_blocks)
            with ThreadPoolExecutor(max_workers=len(tool_blocks)) as executor:
                futures = {executor.submit(_execute_tool, b): i
                           for i, b in enumerate(tool_blocks)}
                for future in as_completed(futures):
                    tool_results[futures[future]] = future.result()

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Unexpected stop reason — return whatever text we have
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
