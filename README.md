# ✈️ Travel Itinerary Agent

A conversational AI travel planner powered by **Claude Sonnet** (`tool_use`) and a stack of completely **free, keyless APIs**.

Ask it things like:
- *"I want to visit New York for 3 days. I love historical places."*
- *"Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP."*
- *"Recommend the best ramen restaurants in Tokyo."*
- *"Add more restaurants to Day 2."* ← multi-turn follow-up

---

## Quick Start

```bash
cd travel-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

streamlit run src/ui/app.py
```

Open **http://localhost:8501**

---

## Architecture

```
User → Streamlit UI → travel_agent.py (Claude tool_use loop)
                              │
            ┌─────────────────┼──────────────────┐
            ▼                 ▼                  ▼
      geocode_city       get_weather        get_country_info
      (Nominatim)       (Open-Meteo)       (REST Countries)
            │
      get_places / get_restaurants   get_currency_rate
      (Overpass / OSM)               (Frankfurter)
            │
      get_route_time
      (OSRM — walking order)
```

Claude runs a `while True` tool_use loop. All parallel tool calls (weather + country + currency) are executed concurrently via `ThreadPoolExecutor`.

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

Only `ANTHROPIC_API_KEY` is required.

---

## Project Structure

```
src/
  tools/          # One file per API (geocode, weather, places, currency, country, routing)
  models/         # Pydantic v2 — Place, ItineraryDay, TravelPlan, etc.
  agents/         # Claude tool_use orchestrator loop
  ui/             # Streamlit chat interface
tests/
  test_tools.py   # Unit tests for all 6 tool functions (no API key needed)
  test_agent.py   # Integration test (requires ANTHROPIC_API_KEY)
```

## Running Tests

```bash
# Tool tests (no API key required)
python tests/test_tools.py

# Agent integration test (requires ANTHROPIC_API_KEY)
python tests/test_agent.py
```
