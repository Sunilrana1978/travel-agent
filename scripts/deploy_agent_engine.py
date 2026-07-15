"""Deploy app/agent_engine_app.py's travel_agent_app to Vertex AI Agent Engine.

Replaces `agents-cli deploy`, which has no --env flag and no deployment target
compatible with vertexai.agent_engines.templates.adk.AdkApp in this SDK version.
Talks to the vertexai.agent_engines SDK directly instead.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import vertexai
from vertexai import agent_engines


def _export_requirements() -> str:
    """Generate a pinned requirements list from pyproject.toml/uv.lock."""
    result = subprocess.run(
        [
            "uv",
            "export",
            "--no-dev",
            "--no-hashes",
            "--no-annotate",
            "--no-header",
            "--format",
            "requirements-txt",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=REPO_ROOT
    ) as f:
        f.write(result.stdout)
        return f.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--env", required=True, choices=["staging", "prod"])
    args = parser.parse_args()

    from app.agent_engine_app import travel_agent_app

    display_name = f"travel-agent-{args.env}"
    staging_bucket = f"gs://{args.project}-staging"
    logs_bucket = f"{args.project}-logs"
    service_account = f"agent-engine-runtime@{args.project}.iam.gserviceaccount.com"

    vertexai.init(
        project=args.project,
        location=args.region,
        staging_bucket=staging_bucket,
    )

    requirements_path = _export_requirements()
    try:
        existing = list(
            agent_engines.list(filter=f'display_name="{display_name}"')
        )

        deploy_kwargs = dict(
            requirements=requirements_path,
            display_name=display_name,
            extra_packages=["app"],
            service_account=service_account,
            env_vars={"LOGS_BUCKET_NAME": logs_bucket},
        )

        if existing:
            engine = existing[0]
            print(f"Updating existing deployment: {engine.resource_name}")
            engine.update(agent_engine=travel_agent_app, **deploy_kwargs)
        else:
            print(f"Creating new deployment: {display_name}")
            engine = agent_engines.create(travel_agent_app, **deploy_kwargs)

        print(f"Deployed: {engine.resource_name}")
    finally:
        Path(requirements_path).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
