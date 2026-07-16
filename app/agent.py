"""
Travel Agent — Vertex AI Agent Engine entry point.

This module:
  - Configures Vertex AI ADC (Application Default Credentials) authentication.
  - Loads the fully configured modular multi-agent system from travel_agent package.
"""
import os

import google.auth

# --- Vertex AI Authentication ---
# Uses Application Default Credentials (gcloud auth application-default login)
# instead of GOOGLE_API_KEY, which is required for Vertex AI Agent Engine.
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-west1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Now import the fully configured modular multi-agent definitions
from app.travel_agent.prompts import SYSTEM_PROMPT  # noqa: F401, E402
from app.travel_agent.travel_agent import app, root_agent  # noqa: E402

__all__ = ["root_agent", "app", "SYSTEM_PROMPT"]
