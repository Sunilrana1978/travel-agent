"""
Sub-agent definitions and tool shims for the Multi-Agent Travel Planner.
"""
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from app.tools import (
    geocode_city,
    get_country_info,
    get_currency_rate,
    get_places,
    get_restaurants,
    get_route_time,
    get_weather,
)

# ── Geographic Context Agent ─────────────────────────────────────────────────
geographic_agent = Agent(
    name="geographic_agent",
    model="gemini-2.5-flash",
    description="Geographic context specialist. Geocodes cities, fetches weather, country info, and exchange rates.",
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
    description="Dining and POI specialist. Finds sightseeing places and restaurants based on user interests.",
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

# Wrap sub-agents as tools for orchestration
geographic_tool = AgentTool(agent=geographic_agent)
poi_tool = AgentTool(agent=poi_agent)
logistics_tool = AgentTool(agent=logistics_agent)
