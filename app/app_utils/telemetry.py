"""
Telemetry setup for Vertex AI Agent Engine.

Configures OpenTelemetry and Google GenAI instrumentation so that traces,
spans, and model call content are captured in Cloud Trace / GCS.
"""
import logging
import os


def setup_telemetry() -> str | None:
    """
    Configure OpenTelemetry and GenAI telemetry.

    Environment variables (set by agents-cli infra):
        GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY: Set to "true" to enable.
        LOGS_BUCKET_NAME: GCS bucket for raw trace/content exports.
        OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT:
            Set "true" in staging to capture prompt/response content for debugging.
            Keep "false" in production for privacy.

    Returns:
        The GCS bucket name if configured, otherwise None.
    """
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )

    if bucket:
        logging.info(
            "Telemetry enabled: bucket=%s, capture_content=%s",
            bucket,
            capture_content,
        )
    else:
        logging.warning(
            "LOGS_BUCKET_NAME not set — telemetry will run without GCS export."
        )

    return bucket
