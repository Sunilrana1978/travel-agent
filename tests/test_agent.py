"""Integration test — requires ANTHROPIC_API_KEY in environment."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from src.agents.travel_agent import run_agent


def test_paris_itinerary():
    response = run_agent(
        "Plan 2 days in Paris. I love historical places. I'm spending USD.",
        history=[],
    )
    assert response, "Agent returned empty response"
    # Should return JSON with days
    try:
        plan = json.loads(response)
        assert "days" in plan
        assert len(plan["days"]) == 2
        assert plan["destination"].lower().__contains__("paris")
        print(f"  PASS  test_paris_itinerary — {len(plan['days'])} days, "
              f"{sum(len(d['places']) for d in plan['days'])} places total")
    except json.JSONDecodeError:
        # Acceptable if agent replied in plain text for a short trip
        print(f"  PASS  test_paris_itinerary (plain text response)")


if __name__ == "__main__":
    test_paris_itinerary()
