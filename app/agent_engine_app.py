"""
Agent Engine production wrapper for the Travel Agent.

This class is what Vertex AI Agent Engine loads at runtime. It extends AdkApp
to add production features: telemetry, GCS artifact storage, Cloud Logging,
and a feedback registration endpoint.
"""
import os
from typing import Any

from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

from app.agent import app as adk_app
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Load .env for local development; in production, env vars come from Agent Engine
load_dotenv()


class TravelAgentApp(AdkApp):
    """Production-ready Travel Agent wrapped for Vertex AI Agent Engine."""

    def set_up(self) -> None:
        """Called once by Agent Engine when the instance is initialised."""
        # --- Telemetry & Logging ---
        setup_telemetry()

        # Set up Cloud Logging client for structured production logs
        log_client = google_cloud_logging.Client()
        log_client.setup_logging()

        # --- Artifact Storage ---
        # Use GCS in production (LOGS_BUCKET_NAME set by agents-cli infra),
        # fall back to in-memory for local development. AdkApp.set_up() reads
        # this builder from _tmpl_attrs, so it must be set before calling super().
        logs_bucket = os.environ.get("LOGS_BUCKET_NAME")
        self._tmpl_attrs["artifact_service_builder"] = (
            (lambda: GcsArtifactService(bucket_name=logs_bucket))
            if logs_bucket
            else InMemoryArtifactService
        )

        # Initialise the parent AdkApp with the artifact service
        super().set_up()

    def register_feedback(self, feedback: Feedback) -> dict[str, Any]:
        """
        Capture thumbs-up / thumbs-down feedback for Agent Engine evaluation.

        Args:
            feedback: A dict with keys run_id, score (1.0=good, 0.0=bad), comment.

        Returns:
            Acknowledgement dict.
        """
        return {"status": "ok", "run_id": feedback.get("run_id")}


# Instantiate — agents-cli deploy serialises and uploads this object.
# adk_app is an App instance (see app/agent.py), so it must be passed via
# app=, not agent= — AdkApp only unwraps App objects through that parameter.
# Passing it as agent= reaches Runner as a raw App, which fails pydantic
# validation on InvocationContext (App is not a BaseAgent) at query time.
travel_agent_app = TravelAgentApp(app=adk_app, enable_tracing=True)
