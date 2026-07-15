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
- **`app/agent.py`** — Vertex AI Agent Engine entry point. Re-declares `root_agent` and
  wraps it in an ADK `App`, but switches auth to Vertex ADC
  (`google.auth.default()` + `GOOGLE_GENAI_USE_VERTEXAI=True`) instead of `GOOGLE_API_KEY`.
  This is what `agents-cli deploy` / `app/agent_engine_app.py` upload.
- **`app/agent_engine_app.py`** — `TravelAgentApp(AdkApp)`, the production wrapper actually
  loaded by Agent Engine at runtime. Adds telemetry (`app/app_utils/telemetry.py`), Cloud
  Logging, GCS-backed artifact storage, and a `register_feedback` endpoint
  (`app/app_utils/typing.py` defines the `Feedback` TypedDict). Artifact storage is wired via
  `self._tmpl_attrs["artifact_service_builder"]` set *before* calling `super().set_up()` —
  `AdkApp.set_up()` only picks up a custom artifact service through that key, so don't
  construct the service object without assigning it there.

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
- **Production (Agent Engine)**: Vertex AI ADC / Workload Identity, no key required
  (used by `app/agent.py` / `app/agent_engine_app.py`). Never commit `.env`.

## Deploying to Google Cloud

Full walkthrough lives in the README's "Deploying to Google Cloud" section.
**`agents-cli deploy`/`agents-cli infra` do not work here** — every published `agents-cli`
version (0.1.0–1.1.0) only supports `agent_runtime` as a deployment target (not
`agent_engine`) and requires a `agents-cli-manifest.yaml` this repo doesn't have.
Deployment goes through `scripts/deploy_agent_engine.py` instead, which calls
`vertexai.agent_engines.create()`/`.update()` directly against `app/agent_engine_app.py`'s
`travel_agent_app`:

```bash
make deploy-staging   # uv run python scripts/deploy_agent_engine.py --project=travel-agent-502518 --region=us-west1 --env=staging
make deploy-prod      # ...--env=prod
```

Infra (project `travel-agent-502518`, region `us-west1`) is provisioned: billing linked,
`aiplatform`/`cloudbuild`/`cloudresourcemanager` APIs enabled, `gs://travel-agent-502518-staging`
and `-logs` buckets, and an `agent-engine-runtime` service account with
`aiplatform.user`/`logging.logWriter`/`cloudtrace.agent` (project-level) plus
`storage.objectAdmin` (scoped to the two buckets).

Gotchas hit while setting this up, in case they recur:
- **ADC quota project must match the target project** (`gcloud auth application-default
  set-quota-project travel-agent-502518`), or the GCS upload step fails with an opaque 403.
- **`AdkApp(app=..., ...)` vs `AdkApp(agent=..., ...)`**: `app/agent.py`'s `app` object is
  an ADK `App`, not a `BaseAgent`. It must be passed to `TravelAgentApp` via `app=`, not
  `agent=` — passing it as `agent=` builds and deploys without error, but every query then
  fails server-side with a pydantic `InvocationContext` validation error, since `Runner`
  only unwraps `App` objects passed through the `app=` slot. This only surfaces at query
  time against a live deployment, not in local dev or tests.
- `.update()` calls on an existing Agent Engine occasionally fail once with a generic
  "Reasoning Engine failed to be updated" (no further detail in Cloud Logging); a retry
  has succeeded both times this happened.

**Cloud Build**: `.cloudbuild/pr_checks.yaml`/`deploy.yaml` exist and their APIs are
enabled, but no trigger is connected to this GitHub repo yet (`gh pr checks` returns no
checks) — that requires an interactive GitHub App authorization in the Cloud Build
console. See README for the exact steps.

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
