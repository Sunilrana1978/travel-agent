"""Robustness and error handling tests for the travel agent."""
import json
import os
import sys
import uuid

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.travel_agent import run_agent


def test_case(name: str, prompt: str):
    print(f"\n========================================\nTEST CASE: {name}\nPrompt: '{prompt}'\n========================================")
    session_id = str(uuid.uuid4())
    try:
        response = run_agent(prompt, session_id=session_id)
        print("Response received:")
        print(response)

        # Clean up markdown code block fences if present
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()

        try:
            data = json.loads(clean_response)
            print("\nResult: SUCCESS (Valid JSON returned)")
            if "days" in data:
                print(f"Number of days planned: {len(data['days'])}")
                print(f"Destination field: {data.get('destination')}")
            else:
                print("JSON does not contain 'days' field.")
        except json.JSONDecodeError:
            print("\nResult: GRACEFUL FALLBACK (Response is plain text/not valid JSON)")

    except Exception as e:
        print(f"\nResult: FAILED / EXCEPTION THROWN: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting robustness and error tests...")

    # 1. Invalid destination (Atlantis)
    test_case("Invalid Destination - Atlantis", "Plan a trip to Atlantis")

    # 2. Invalid destination (XxXNotACityXxX)
    test_case("Invalid Destination - XxXNotACityXxX", "Plan a trip to XxXNotACityXxX")

    # 3. Garbage input
    test_case("Garbage Input", "12345!@#$")

    # 4. Extremely long trip
    test_case("Extremely Long Trip (30 days)", "Plan 30 days in Paris")

    print("\nAll robustness tests finished.")
