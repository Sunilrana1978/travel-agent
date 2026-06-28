# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GOOGLE_API_KEY to .env (from https://aistudio.google.com/app/apikey)
```

## Running the app

```bash
streamlit run src/ui/app.py
```

## Tests

```bash
# Tool integration tests — hit real free APIs, no key needed
python tests/test_tools.py

# Agent integration test — requires GOOGLE_API_KEY
python tests/test_agent.py
```

There is no test framework (pytest etc.) — tests are plain Python scripts with a manual runner at `if __name__ == "__main__"`. Run individual test functions by calling them directly or adding them to the `tests` list in the script.

## Architecture

```
User → Streamlit UI (src/ui/app.py)
         └─► run_agent() (src/agents/travel_agent.py)
               └─► Google ADK Runner + Gemini 2.5 Flash
                     └─► tools (src/tools/)
```

**Agent layer** (`src/agents/travel_agent.py`): Uses `google-adk` with `gemini-2.5-flash`. The agent is initialized once at module level as a singleton (`_agent`, `_runner`, `_session_service`). Conversations are keyed by `session_id` (a UUID per browser session). `run_agent()` is a sync wrapper around `asyncio.run(_run_async(...))`.

**Tools** (`src/tools/`): Seven plain Python functions registered directly with the ADK agent — `geocode_city`, `get_weather`, `get_places`, `get_restaurants`, `get_currency_rate`, `get_country_info`, `get_route_time`. All call free, keyless public APIs (Nominatim, Open-Meteo, Overpass/OSM, Frankfurter, REST Countries, OSRM). `geocode_city` uses `@lru_cache` to avoid redundant geocoding within a session.

**Models** (`src/models/itinerary.py`): Pydantic v2 dataclasses (`TravelPlan`, `ItineraryDay`, `Place`, etc.) that describe the JSON schema the agent is instructed to return. These are documentation/validation only — the agent output is parsed with `json.loads()` in the UI, not via Pydantic.

**UI** (`src/ui/app.py`): Streamlit chat interface. Tries to parse each agent response as `TravelPlan` JSON; renders it as structured cards (`render_itinerary`) + sidebar (`render_sidebar`) if valid, otherwise falls back to plain markdown. Chat history is stored in `st.session_state`.

## Key env vars

| Var | Required | Default |
|-----|----------|---------|
| `GOOGLE_API_KEY` | Yes | — |
| `NOMINATIM_USER_AGENT` | No | `TravelAgent/1.0` |
| `OVERPASS_URL` | No | `https://overpass-api.de/api/interpreter` |
| `OSRM_URL` | No | `http://router.project-osrm.org` |
| `DEFAULT_CURRENCY_FROM` | No | `USD` |

> **Note**: The README references Claude/Anthropic but the codebase was migrated to Google ADK + Gemini. `GOOGLE_API_KEY` is the correct required key.
