# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
make install          # installs uv (if missing) and runs `uv sync --all-groups`
cp .env.example .env
# Add GOOGLE_API_KEY to .env (from https://aistudio.google.com/app/apikey)
```

## Running the app

```bash
make ui               # Streamlit chat UI at :8502 (app/ui/app.py), uses GOOGLE_API_KEY
make playground        # ADK web playground at :8501 — hot-reload dev console, select the 'app' folder
```

## Lint & tests

```bash
make lint             # ruff check app/ tests/
make lint-fix          # ruff check --fix app/ tests/
make test             # pytest tests/test_tools.py tests/test_agent.py -v
make test-all          # pytest tests/ -v (includes slower e2e scenarios)
```

- `test_tools.py`, `test_ui_exports.py` — hit real free keyless APIs / local export code, no key needed.
- `test_agent.py`, `test_multi_turn_flow.py`, `test_robustness_errors.py`, `test_e2e_scenarios.py` —
  require `GOOGLE_API_KEY`, drive `run_agent()` end-to-end.
- Run a single test: `uv run pytest tests/test_tools.py::test_geocode -v`.
- All tests import from `app.*` (not `src.*` — the old `src/` tree was removed; `app/` is the only
  source tree now, following the `agents-cli` convention).

## Architecture

```
User → Streamlit UI (app/ui/app.py)
         └─► run_agent() (app/agents/travel_agent.py)
               └─► Google ADK Runner + Gemini 2.5 Flash
                     └─► tools (app/tools/)
```

There are two separate agent entry points, both built from the same
`SYSTEM_PROMPT` / tools list defined in `app/agents/travel_agent.py`:

- **`app/agents/travel_agent.py`** — local dev path. Builds its own `Agent` + `Runner` +
  `InMemorySessionService`, keyed by `session_id` (a UUID per browser session), auth via
  `GOOGLE_API_KEY`. `run_agent()` is a sync wrapper around `asyncio.run(_run_async(...))`
  with retry-on-`ServerError` (3 attempts, backoff).
- **`app/agent.py`** — Agent Runtime entry point. Re-declares `root_agent` and wraps it in
  an ADK `App`, switching auth to Vertex ADC (`google.auth.default()` +
  `GOOGLE_GENAI_USE_VERTEXAI=True`) instead of `GOOGLE_API_KEY`.
- **`app/fast_api_app.py`** — the container's entry point (`uvicorn app.fast_api_app:app`,
  see `Dockerfile`). One FastAPI app serves three surfaces at once: native ADK web/API
  routes (`get_fast_api_app`), A2A protocol routes (`app/app_utils/a2a.py`), and a
  `/api/reasoning_engine` + `/api/stream_reasoning_engine` compatibility shim
  (`app/app_utils/reasoning_engine_adapter.py`) so the Vertex Console Playground and Gemini
  Enterprise registration keep working. Session/artifact services are centralized in
  `app/app_utils/services.py` (registered under `shared://` URIs) so all three surfaces see
  the same sessions. Telemetry setup (`app/app_utils/telemetry.py`) must run *before*
  `get_fast_api_app` — the OTel resource is fixed at tracer-provider creation.
  `app/app_utils/typing.py` defines the `Feedback` TypedDict used by the `/feedback` route
  (must import from `typing_extensions`, not `typing` — pydantic v2 rejects
  `typing.TypedDict` on Python < 3.12 when used as a route parameter).

**Tools** (`app/tools/`): one file per free, keyless public API — `geocode_tool.py`
(Nominatim, `@lru_cache`d), `weather_tool.py` (Open-Meteo), `places_tool.py`
(Overpass/OSM — `get_places` + `get_restaurants`), `currency_tool.py` (Frankfurter),
`country_tool.py` (REST Countries), `routing_tool.py` (OSRM). All exported from
`app/tools/__init__.py` and registered directly as ADK tool functions in both
`travel_agent.py` and `agent.py`.

To add a new tool: create `app/tools/my_tool.py`, export it from `app/tools/__init__.py`,
add it to the `tools=[...]` list in **both** `app/agents/travel_agent.py` and
`app/agent.py`, and add a test in `tests/test_tools.py`.

**Models** (`app/models/itinerary.py`): Pydantic v2 dataclasses (`TravelPlan`,
`ItineraryDay`, `Place`, etc.) describing the JSON schema the agent is instructed to
return via `SYSTEM_PROMPT`. Documentation/validation only — the UI parses agent output
with `json.loads()`, not via these Pydantic models.

**UI** (`app/ui/app.py`, `app/ui/export.py`): Streamlit chat interface. Tries to parse
each agent response as `TravelPlan` JSON and renders structured day cards + sidebar if
valid, otherwise falls back to plain markdown. `export.py` handles PDF/Markdown download
(fpdf2). Chat history lives in `st.session_state`.

## Auth model

- **Local dev**: `GOOGLE_API_KEY` in `.env` (used by `app/agents/travel_agent.py`).
- **Production (Agent Runtime)**: Vertex AI ADC / Workload Identity, no key required
  (used by `app/agent.py` / `app/fast_api_app.py`). Never commit `.env`.

## Deploying to Google Cloud

Full walkthrough lives in the README's "Deploying to Google Cloud" section. This project
is scaffolded with `agents-cli` (see `agents-cli-manifest.yaml`), deployment target
`agent_runtime` — container-based: `agents-cli deploy` builds the image from `Dockerfile`
(`uvicorn app.fast_api_app:app`) and Agent Runtime hosts it. Deploy manually with:

```bash
make deploy-staging   # uv run agents-cli deploy --project=travel-agent-502518 --region=us-west1 --service-name=travel-agent-staging --no-confirm-project
make deploy-prod      # ...--service-name=travel-agent-prod
```

**CI/CD**: `.cloudbuild/pr_checks.yaml` (lint + unit tests on PRs), `.cloudbuild/staging.yaml`
(deploy to staging + load test + trigger prod build), `.cloudbuild/deploy-to-prod.yaml`
(deploy to prod) — all call `agents-cli deploy` directly, provisioned via
`agents-cli infra cicd`. See README for the exact `infra cicd` invocation and required
GitHub ↔ Cloud Build connection steps.

**Infra** (project `travel-agent-502518`, region `us-west1`) needs re-provisioning via
`agents-cli infra cicd` (Terraform-managed this time — state stored remotely in a GCS
bucket, not local files) — the buckets and service account from the previous manual
`gcloud`-based setup were deleted and are no longer assumed to exist.

Gotchas hit while setting this up, in case they recur:
- **ADC quota project must match the target project** (`gcloud auth application-default
  set-quota-project travel-agent-502518`), or GCS upload steps fail with an opaque 403.
- **`AdkApp(app=..., ...)` vs `AdkApp(agent=..., ...)`**: an ADK `App` object must be passed
  via `app=`, not `agent=` — `agent=` builds without error but fails every query at runtime
  with a pydantic `InvocationContext` validation error. Only surfaces against a live
  deployment, not in local dev or tests. (This bug lived in the old
  `app/agent_engine_app.py`, now removed in favor of `app/fast_api_app.py`.)
- **`typing.TypedDict` vs `typing_extensions.TypedDict`**: pydantic v2 rejects
  `typing.TypedDict` on Python < 3.12 when the type is used directly as a FastAPI route
  parameter (as `Feedback` is in `/feedback`). Use `typing_extensions.TypedDict`.

## Key env vars

| Var | Required | Default |
|-----|----------|---------|
| `GOOGLE_API_KEY` | Yes (local dev) | — |
| `NOMINATIM_USER_AGENT` | No | `TravelAgent/1.0` |
| `OVERPASS_URL` | No | `https://overpass-api.de/api/interpreter` |
| `OSRM_URL` | No | `http://router.project-osrm.org` |
| `DEFAULT_CURRENCY_FROM` | No | `USD` |

## Screenshots

App screenshots live in `docs/` and are referenced in the README:

- `docs/screenshot.png` — New York 3-day itinerary (main UI overview)
- `docs/screenshot-delhi.png` — Delhi 2-day itinerary
- `docs/screenshot-sydney.png` — Sydney 2-day outdoor itinerary
- `docs/screenshot-landing.png` — Landing page with quick-start prompts
- `docs/screenshot-barcelona-new.png`, `docs/screenshot-map.png` — Barcelona itinerary and place cards

When adding new screenshots, copy the image into `docs/` and add it to the Screenshots
table in `README.md`.
