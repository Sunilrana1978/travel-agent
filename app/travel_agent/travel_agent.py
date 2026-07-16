import asyncio
import time

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import ServerError

# Modular imports
from app.travel_agent.prompts import SYSTEM_PROMPT_ORCHESTRATOR
from app.travel_agent.sub_agents import geographic_tool, logistics_tool, poi_tool

load_dotenv()

_APP_NAME = "travel_agent"
_USER_ID = "user"

_session_service = InMemorySessionService()

# ── Lead Orchestrator Agent ─────────────────────────────────────────────────
root_agent = _agent = Agent(
    name=_APP_NAME,
    model="gemini-2.5-flash",
    description="Expert travel itinerary planner that creates day-by-day trips.",
    instruction=SYSTEM_PROMPT_ORCHESTRATOR,
    tools=[geographic_tool, poi_tool, logistics_tool],
)

# App object — used by app/agent.py and app/fast_api_app.py
app = App(name=_APP_NAME, root_agent=root_agent)

_memory_service = InMemoryMemoryService()

_runner = Runner(
    agent=_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
    memory_service=_memory_service,
)


async def _run_async(user_message: str, session_id: str) -> str:
    session = await _session_service.get_session(
        app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
    )
    if session is None:
        await _session_service.create_session(
            app_name=_APP_NAME, user_id=_USER_ID, session_id=session_id
        )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    final_text = ""
    async for event in _runner.run_async(
        user_id=_USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""

    return final_text


def run_agent(user_message: str, session_id: str) -> str:
    """Run the travel agent for one user turn. Returns the assistant's response text."""
    for attempt in range(3):
        try:
            return asyncio.run(_run_async(user_message, session_id))
        except ServerError:
            if attempt < 2:
                time.sleep(4 * (attempt + 1))
            else:
                raise
    return ""  # unreachable
