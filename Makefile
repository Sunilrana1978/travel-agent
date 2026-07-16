# ==============================================================================
# Travel Agent — Developer Convenience Makefile
# All commands use uv as the package manager.
# ==============================================================================

.PHONY: install playground lint test deploy-staging deploy-prod

# Install all dependencies (including dev group)
install:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync --all-groups

# Run local ADK web playground (hot-reload, no cloud needed)
# Open http://localhost:8501 — select the 'app' folder in the UI
playground:
	@echo "=================================================="
	@echo "  🚀 Starting Travel Agent Playground..."
	@echo "  📍 Open: http://localhost:8501"
	@echo "  🗂  Select the 'app' folder in the ADK UI"
	@echo "=================================================="
	PYTHONPATH=. uv run adk web app/ --port 8501

# Run Streamlit UI locally (uses GOOGLE_API_KEY from .env)
ui:
	PYTHONPATH=. uv run streamlit run app/ui/main.py --server.port 8502


# Lint — ruff check
lint:
	uv run ruff check app/ tests/

# Lint and fix automatically
lint-fix:
	uv run ruff check --fix app/ tests/

# Run unit tests
test:
	uv run pytest tests/test_tools.py tests/test_agent.py -v

# Run all tests (including e2e, slower)
test-all:
	uv run pytest tests/ -v

# Deploy to staging Agent Runtime (container-based, via agents-cli deploy)
deploy-staging:
	uv run agents-cli deploy \
		--project=travel-agent-502518 \
		--region=us-west1 \
		--service-name=travel-agent-staging \
		--no-confirm-project

# Deploy to production Agent Runtime (separate GCP project from staging)
deploy-prod:
	uv run agents-cli deploy \
		--project=travel-agent-prod-637490 \
		--region=us-west1 \
		--service-name=travel-agent-prod \
		--no-confirm-project
