# ✈️ Travel Itinerary Agent

A conversational AI travel planner powered by **Gemini 2.5 Flash** (via Google ADK) and a stack of completely **free, keyless APIs**.

![Travel Itinerary Agent](docs/screenshot-landing.png)

## Features

- **Day-by-day itinerary** — 3–4 themed stops per day with descriptions, tips, and opening hours
- **Interactive route map** — Leaflet map per day with numbered markers and a dashed route line connecting stops in order
- **Live weather** — forecast for each day of the trip via Open-Meteo
- **Budget estimator** — budget / mid-range / luxury daily cost in the destination currency
- **Packing list** — tailored to weather and trip type (beach, hiking, city, etc.)
- **Hotel area suggestions** — best neighbourhoods to stay with price range
- **Country & currency sidebar** — flag, capital, language, timezone, live FX rate
- **Download itinerary** — export as PDF or Markdown
- **Multi-turn chat** — refine the plan ("add more restaurants to Day 2", "what's the weather on Day 3?")

---

## Screenshots

| Landing — 8 quick-start prompts | Barcelona — itinerary with packing list & hotel cards |
|---|---|
| ![Landing page](docs/screenshot-landing.png) | ![Barcelona itinerary](docs/screenshot-barcelona-new.png) |

| Barcelona — place cards with tips & walk times | New York — 3 days historical |
|---|---|
| ![Place cards](docs/screenshot-map.png) | ![New York itinerary](docs/screenshot.png) |

| Delhi — 2 days | Sydney — 2 days outdoors |
|---|---|
| ![Delhi itinerary](docs/screenshot-delhi.png) | ![Sydney itinerary](docs/screenshot-sydney.png) |

---

## Example prompts

- *"I want to visit New York for 3 days. I love historical places."*
- *"Plan 5 days in Paris focused on art museums and cafés. Show prices in GBP."*
- *"Recommend the best ramen restaurants in Tokyo."*
- *"Plan 3 days in Bali focused on beaches and local culture."*
- *"Plan 4 days in Rome. I love ancient history and architecture."*
- *"Add more restaurants to Day 2."* ← multi-turn follow-up

---

## Setup

```bash
cd travel-agent
make install    # installs uv (if needed) and syncs all dependencies via pyproject.toml

cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY (from https://aistudio.google.com/app/apikey)
```

---

## Running the App

### Option 1 — Streamlit UI (chat interface)

```bash
make ui
```

Open **http://localhost:8502**

Chat interface with collapsible day cards, interactive route maps, weather, country info, live exchange rates, and PDF/Markdown download.

### Option 2 — ADK Web Playground (agent dev console)

```bash
make playground
```

Open **http://localhost:8501** and select the `app` folder.

Google ADK developer console — useful for inspecting tool calls, intermediate steps, and agent traces.

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

## Deploying to Google Cloud (Vertex AI Agent Engine)

The app is built on the [`agents-cli`](https://pypi.org/project/google-agents-cli/)
convention: `app/` is deployed as-is to Vertex AI Agent Engine, with Google Cloud Build
handling CI/CD. Deployment target: project `travel-agent-502518`, region `us-west1`.

> **Status in this repo:** the code (`app/`, `pyproject.toml`, `.cloudbuild/`) is in place,
> but the one-time GCP infra provisioning and CI/CD wiring below have **not** been run yet —
> `gh pr checks` currently reports no checks on PRs, and there's no `deployment/terraform/`
> directory. Steps 1–2 below are one-time setup that needs to happen before `make
> deploy-staging` / `make deploy-prod` or automatic PR/push deploys will work.

> **Note:** `agents-cli infra`/`agents-cli deploy` do **not** work for this project —
> every published `agents-cli` version (0.1.0–1.1.0) only supports `agent_runtime` as a
> deployment target and requires a `agents-cli-manifest.yaml` this repo doesn't have.
> Deployment instead goes straight through the `vertexai.agent_engines` SDK via
> `scripts/deploy_agent_engine.py`, which is what `make deploy-staging`/`deploy-prod` and
> `.cloudbuild/deploy.yaml` actually call.

### Prerequisites

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project travel-agent-502518
```
The quota-project step matters: if ADC's quota project doesn't match the deploy target,
the GCS upload step in `deploy_agent_engine.py` fails with an opaque 403.

### 1. Infrastructure (already provisioned for `travel-agent-502518` / `us-west1`)

```bash
gcloud billing projects link travel-agent-502518 --billing-account=<your-billing-account>
gcloud services enable aiplatform.googleapis.com cloudbuild.googleapis.com cloudresourcemanager.googleapis.com \
  --project=travel-agent-502518

gcloud storage buckets create gs://travel-agent-502518-staging --project=travel-agent-502518 --location=us-west1 --uniform-bucket-level-access
gcloud storage buckets create gs://travel-agent-502518-logs --project=travel-agent-502518 --location=us-west1 --uniform-bucket-level-access

gcloud iam service-accounts create agent-engine-runtime --project=travel-agent-502518
SA=agent-engine-runtime@travel-agent-502518.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding travel-agent-502518 --member="serviceAccount:$SA" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding travel-agent-502518 --member="serviceAccount:$SA" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding travel-agent-502518 --member="serviceAccount:$SA" --role="roles/cloudtrace.agent"
gcloud storage buckets add-iam-policy-binding gs://travel-agent-502518-staging --member="serviceAccount:$SA" --role="roles/storage.objectAdmin"
gcloud storage buckets add-iam-policy-binding gs://travel-agent-502518-logs --member="serviceAccount:$SA" --role="roles/storage.objectAdmin"
```
No Artifact Registry is needed — Agent Engine builds are source-based (a GCS-staged
tarball), not a container you push yourself.

### 2. Deploy

```bash
make deploy-staging   # uv run python scripts/deploy_agent_engine.py --project=travel-agent-502518 --region=us-west1 --env=staging
make deploy-prod       # ...--env=prod
```

`scripts/deploy_agent_engine.py` exports pinned deps via `uv export`, then calls
`vertexai.agent_engines.create()`/`.update()` directly against `app/agent_engine_app.py`'s
`travel_agent_app` (looked up by `display_name=f"travel-agent-{env}"`). Builds take
5–10+ minutes; occasional single-retry activation failures on `.update()` have been
observed and are usually transient.

### 3. Cloud Build CI/CD (partly manual)

`aiplatform`/`cloudbuild` APIs are enabled, but no Cloud Build trigger is wired to this
GitHub repo yet — that requires authorizing the Cloud Build GitHub App interactively:
Cloud Build console → Repositories → Connect Repository → authorize
`Sunilrana1978/travel-agent`. After connecting, create triggers for
`.cloudbuild/pr_checks.yaml` (on PRs) and `.cloudbuild/deploy.yaml` (on push to
`staging`/`main`, with `_ENV=staging`/`prod` substitutions) via `gcloud builds triggers
create github`. Until then, `make deploy-staging`/`deploy-prod` above are the only way
to deploy.

### Auth model

- **Local dev** (`make ui` / `make playground`) uses `GOOGLE_API_KEY` from `.env`.
- **Production** (Agent Engine) uses Vertex AI ADC / Workload Identity via the
  `agent-engine-runtime` service account — no API key needed. `app/agent.py` switches
  auth automatically via `google.auth.default()` + `GOOGLE_GENAI_USE_VERTEXAI=True`.

---

## Free API Stack

| API | Purpose | Key? |
|-----|---------|------|
| Open-Meteo | Weather forecast | No |
| Overpass / OSM | Places, POIs, restaurants | No |
| Nominatim | City → lat/lon | No |
| Frankfurter | Currency exchange rates | No |
| REST Countries | Country info, flag, timezone | No |
| OSRM | Walking/driving times | No |

Only `GOOGLE_API_KEY` is required.

---

## Project Structure

```
app/
  agents/         # Google ADK agent + system prompt (travel_agent.py)
  agent.py        # Vertex AI Agent Engine entry point (root_agent + App, Vertex ADC auth)
  agent_engine_app.py  # Production Agent Engine wrapper (telemetry, GCS, logging)
  tools/          # One file per API (geocode, weather, places, currency, country, routing)
  models/         # Pydantic v2 — Place, ItineraryDay, TravelPlan, etc.
  ui/
    app.py        # Streamlit chat interface with map, cards, sidebar
    export.py     # PDF and Markdown export (fpdf2)
  app_utils/      # Telemetry setup and shared types
tests/
  test_tools.py   # Integration tests for all tool functions (no API key needed)
  test_agent.py   # End-to-end agent test (requires GOOGLE_API_KEY)
.cloudbuild/      # Cloud Build CI/CD — PR checks and staging/prod deploy
```

---

## Running Tests

```bash
make test       # tests/test_tools.py + tests/test_agent.py (test_agent.py needs GOOGLE_API_KEY)
make test-all   # everything, including slower e2e scenarios
```
