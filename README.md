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

    ST["🎈 Streamlit UI\nlocalhost:8502"]
    ADK["🌐 FastAPI Server\nlocalhost:8000"]

    User --> ST & ADK

    subgraph Orchestrator [🤖 Lead Orchestrator Agent]
        ORCH["✨ travel_agent (gemini-2.5-flash)\nCoordinates specialized sub-agents"]
    end

    ST & ADK --> ORCH

    subgraph Agents [🤖 Specialized Sub-Agents]
        GEO["🌍 geographic_agent\n(gemini-2.5-flash)"]
        POI["🏛️ poi_agent\n(gemini-2.5-flash)"]
        LOG["🗺️ logistics_agent\n(gemini-2.5-flash)"]
    end

    ORCH -->|AgentTool| GEO
    ORCH -->|AgentTool| POI
    ORCH -->|AgentTool| LOG

    subgraph Tools [⚙️ Python API Tools]
        GC["📍 geocode_city"]
        WX["🌤️ get_weather"]
        CI["🌍 get_country_info"]
        FX["💱 get_currency_rate"]
        PL["🏛️ get_places / get_restaurants"]
        RT["🗺️ get_route_time"]
    end

    GEO --> GC & WX & CI & FX
    POI --> PL
    LOG --> RT

    style ORCH fill:#4285F4,color:#fff,stroke:#2962FF
    style GEO fill:#FBBC05,color:#fff,stroke:#F86B00
    style POI fill:#ea4335,color:#fff,stroke:#b20a00
    style LOG fill:#34a853,color:#fff,stroke:#1e7e34
    style ST fill:#FF4B4B,color:#fff,stroke:#CC0000
    style ADK fill:#9C27B0,color:#fff,stroke:#7B1FA2
    style User fill:#f5f5f5,stroke:#9E9E9E
```

The ADK agent runs an orchestrated multi-agent workflow. The Lead Orchestrator delegates sub-tasks dynamically to specialized sub-agents wrapped as `AgentTool` instances.

---

## Deploying to Google Cloud (Vertex AI Agent Runtime)

The app is scaffolded with [`agents-cli`](https://pypi.org/project/google-agents-cli/)
(`agents-cli-manifest.yaml`), deployment target `agent_runtime` — container-based:
`agents-cli deploy` builds an image from `Dockerfile` (`uvicorn app.fast_api_app:app`) and
Agent Runtime hosts it. CI/CD runner: Google Cloud Build. **Staging and prod are separate
GCP projects** — `travel-agent-502518` (staging) and `travel-agent-prod-637490` (prod),
both region `us-west1`.

> This template's per-environment resources (service account, BigQuery dataset/connection)
> use project-unique names, so a single project shared between staging and prod causes
> name collisions during `terraform apply` (we hit this the first time — service account
> and BigQuery resources for one environment failed with `409 Already Exists` against the
> other's). Separate projects avoid it entirely, and are what this Terraform module's
> `staging_project_id`/`prod_project_id` split is actually designed around.

> **Status in this repo:** infra is fully provisioned via Terraform
> (`agents-cli infra cicd`) — state is tracked remotely in
> `gs://travel-agent-502518-terraform-state` (prefix `travel-agent/prod`), not implicit in
> ad hoc `gcloud` commands. Both environments have a live Agent Runtime instance, service
> account, logs bucket, and telemetry (BigQuery) dataset/connection.

### Prerequisites

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project travel-agent-502518
gh auth login   # needed for the GitHub <-> Cloud Build connection below
```

### 1. Infra + CI/CD (already provisioned)

```bash
agents-cli infra cicd \
  --staging-project travel-agent-502518 \
  --prod-project travel-agent-prod-637490 \
  --repository-name travel-agent \
  --repository-owner Sunilrana1978 \
  --cicd-runner google_cloud_build \
  --region us-west1
```

Runs in **plan mode** by default (Terraform plan only) — pass `--apply` to actually change
infra. This provisions the Workload Identity Pool + provider, a `cicd_runner_sa` with
cross-project deploy permissions, per-environment `app_sa` service accounts, and the remote
Terraform state bucket. Connecting the GitHub repo to Cloud Build requires either a GitHub
PAT + App Installation ID (`--github-pat` / `--github-app-installation-id`) or the `-i`
interactive flow, which opens a browser prompt you complete yourself — a real OAuth-style
grant, not something to script unattended.

`travel-agent-prod-637490` was created fresh for this — if you ever need to recreate it:
billing must be linked (`gcloud billing projects link <project> --billing-account=<id>`)
and these APIs enabled before Terraform can use it: `aiplatform`, `cloudbuild`,
`cloudresourcemanager`, `bigquery`, `iam`, `run`, `cloudtrace`, `logging`, `serviceusage`,
`artifactregistry`. Note: billing accounts have a project-linking quota — ours was maxed at
5, requiring an old unused project to be unlinked first via `gcloud billing projects
unlink`.

No Artifact Registry setup needed manually — Agent Runtime builds the container from
source.

### 2. Deploy

```bash
make deploy-staging   # uv run agents-cli deploy --project=travel-agent-502518 --region=us-west1 --service-name=travel-agent-staging --no-confirm-project
make deploy-prod      # uv run agents-cli deploy --project=travel-agent-prod-637490 --region=us-west1 --service-name=travel-agent-prod --no-confirm-project
```

Or let CI/CD do it: pushing to `main` triggers `.cloudbuild/staging.yaml` (deploy to
staging in `travel-agent-502518`, run a load test, then trigger the prod build);
`.cloudbuild/deploy-to-prod.yaml` deploys to prod in `travel-agent-prod-637490`, gated by
Cloud Build's manual-approval step (`gcloud builds list --filter="status=PENDING"` +
`gcloud builds approve BUILD_ID`). Both triggers get their target project, service account,
and logs bucket from Terraform-set substitutions — no hardcoded project IDs to keep in
sync. Agent Runtime deploys take 5–10 minutes — `agents-cli deploy --no-wait` / `--status`
let you start and poll instead of blocking.

### Auth model

- **Local dev** (`make ui` / `make playground`) uses `GOOGLE_API_KEY` from `.env`.
- **Production** (Agent Runtime) uses Vertex AI ADC / Workload Identity via the
  Terraform-provisioned `app_sa` — no API key needed. `app/agent.py` switches auth
  automatically via `google.auth.default()` + `GOOGLE_GENAI_USE_VERTEXAI=True`.

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
