"""
Travel Agent — Vertex AI Agent Engine entry point.

This module:
  - Switches authentication to Vertex AI ADC (Application Default Credentials)
    instead of GOOGLE_API_KEY, which is required for Agent Engine.
  - Wraps the ADK Agent in an App object so agents-cli can package and upload it.
"""
import os

import google.auth
from google.adk.agents import Agent
from google.adk.apps import App

from app.agents.travel_agent import SYSTEM_PROMPT
from app.tools import (
    geocode_city,
    get_country_info,
    get_currency_rate,
    get_places,
    get_restaurants,
    get_route_time,
    get_weather,
)

# --- Vertex AI Authentication ---
# Uses Application Default Credentials (gcloud auth application-default login)
# instead of GOOGLE_API_KEY, which is required for Vertex AI Agent Engine.
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-west1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# --- Agent Definition ---
root_agent = Agent(
    name="travel_agent",
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

# --- App object required by Vertex AI Agent Engine ---
# agents-cli deploy uploads this `app` object to Agent Engine.
app = App(name="travel_agent", root_agent=root_agent)
