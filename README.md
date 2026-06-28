# ✈️ Travel Itinerary Agent

A conversational AI travel planner powered by **Gemini 2.5 Flash** (via Google ADK) and a stack of completely **free, keyless APIs**.

![Travel Itinerary Agent](docs/screenshot.png)

Ask it things like:
- *"I want to visit New York for 3 days. I love historical places."*
- *"Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP."*
- *"Recommend the best ramen restaurants in Tokyo."*
- *"Add more restaurants to Day 2."* ← multi-turn follow-up

---

## Setup

```bash
cd travel-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)
```

---

## Running the App

### Option 1 — Streamlit UI (chat interface)

```bash
streamlit run src/ui/app.py
```

Open **http://localhost:8501**

Features a chat interface with collapsible day-by-day itinerary cards, weather forecast, country info, and live exchange rates in the sidebar.

### Option 2 — ADK Web UI (agent dev console)

```bash
adk web .
```

Open **http://127.0.0.1:8000**

Runs the Google ADK developer console — useful for inspecting tool calls, intermediate steps, and agent traces.

---

## Architecture

```mermaid
flowchart TD
    User(["👤 User"])

    ST["🎈 Streamlit UI\nlocalhost:8501"]
    ADK["🌐 ADK Web UI\nlocalhost:8000"]

    GEM["✨ Gemini 2.5 Flash\nvia Google ADK Runner"]

    GC["📍 geocode_city\nNominatim"]
    WX["🌤️ get_weather\nOpen-Meteo"]
    CI["🌍 get_country_info\nREST Countries"]
    FX["💱 get_currency_rate\nFrankfurter"]
    PL["🏛️ get_places / get_restaurants\nOverpass / OSM"]
    RT["🗺️ get_route_time\nOSRM"]

    User --> ST & ADK
    ST & ADK --> GEM
    GEM --> GC & WX & CI & FX
    GC --> PL
    PL --> RT

    style GEM fill:#4285F4,color:#fff,stroke:#2962FF
    style ST fill:#FF4B4B,color:#fff,stroke:#CC0000
    style ADK fill:#34A853,color:#fff,stroke:#1E7E34
    style User fill:#f5f5f5,stroke:#9E9E9E
```

The ADK agent runs a tool-use loop. Parallel tool calls (weather + country + currency) are issued in a single agent step.

---

## Free API Stack

| API | Purpose | Key? |
|-----|---------|------|
| Open-Meteo | Weather forecast | No |
| Overpass / OSM | Places, POIs, restaurants | No |
| Nominatim | City → lat/lon | No |
| Frankfurter | Currency exchange rates | No |
| REST Countries | Country info | No |
| OSRM | Walking/driving times | No |

Only `GOOGLE_API_KEY` is required.

---

## Project Structure

```
src/
  agents/         # Google ADK agent + runner (travel_agent.py)
  agent.py        # Exposes root_agent for adk web
  tools/          # One file per API (geocode, weather, places, currency, country, routing)
  models/         # Pydantic v2 — Place, ItineraryDay, TravelPlan, etc.
  ui/             # Streamlit chat interface (app.py)
tests/
  test_tools.py   # Integration tests for all tool functions (no API key needed)
  test_agent.py   # End-to-end agent test (requires GOOGLE_API_KEY)
```

---

## Running Tests

```bash
# Tool tests — hit real free APIs, no key needed
python tests/test_tools.py

# Agent integration test — requires GOOGLE_API_KEY
python tests/test_agent.py
```
