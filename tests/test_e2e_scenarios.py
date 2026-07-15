import sys
import os
import json
import uuid
import time
import traceback

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.travel_agent import run_agent

SCENARIOS = [
    {
        "id": 1,
        "query": "Plan 4 days in Honolulu, Hawaii. Focused on beaches and surfing. Currency USD.",
        "expected_days": 4,
        "expected_destination": "Honolulu",
    },
    {
        "id": 2,
        "query": "Plan 3 days in Reykjavik in December. Focused on northern lights. Currency ISK.",
        "expected_days": 3,
        "expected_destination": "Reykjavik",
    },
    {
        "id": 3,
        "query": "Plan 2 days in Tokyo. Focused on Michelin-star sushi. Currency JPY.",
        "expected_days": 2,
        "expected_destination": "Tokyo",
    },
    {
        "id": 4,
        "query": "Plan 10 days in London. Focused on history and museums. Currency GBP.",
        "expected_days": 10,
        "expected_destination": "London",
    }
]

def clean_json_response(response_text):
    """Strip markdown code block fences if they are present in the response."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening ```json or ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def test_scenario(scenario):
    query = scenario["query"]
    expected_days = scenario["expected_days"]
    expected_destination = scenario["expected_destination"]
    
    print(f"\n==========================================")
    print(f"Running Scenario {scenario['id']}: {query}")
    print(f"==========================================")
    
    session_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        response = run_agent(query, session_id=session_id)
        duration = time.time() - start_time
        print(f"Execution time: {duration:.2f} seconds")
        
        if not response:
            return {
                "id": scenario["id"],
                "query": query,
                "duration": duration,
                "status": "FAIL",
                "reason": "Empty response returned from agent",
                "is_json": False,
                "conforming": False
            }
            
        # Clean response if wrapped in markdown fences
        cleaned_response = clean_json_response(response)
        had_fences = (cleaned_response != response.strip())
        
        # Try parsing JSON
        try:
            data = json.loads(cleaned_response)
            is_json = True
        except json.JSONDecodeError as je:
            print(f"WARNING: Response was not valid JSON. Response starts with:\n{response[:200]}...")
            return {
                "id": scenario["id"],
                "query": query,
                "duration": duration,
                "status": "FAIL (Plain Text)",
                "reason": f"Response was not valid JSON even after stripping fences. Parse error: {str(je)}",
                "is_json": False,
                "conforming": False,
                "had_fences": had_fences,
                "response_preview": response[:200]
            }
            
        # JSON validation checks
        failures = []
        
        # Check destination
        dest = data.get("destination", "")
        if not dest:
            failures.append("Missing 'destination' key")
        elif expected_destination.lower() not in dest.lower():
            failures.append(f"Destination '{dest}' does not contain expected '{expected_destination}'")
            
        # Check days matching expected
        # Schema indicates "days" key is a list of days, and optionally "total_days"
        days_list = data.get("days", [])
        total_days = data.get("total_days")
        
        if not days_list:
            failures.append("Missing or empty 'days' list")
        elif isinstance(days_list, list):
            if len(days_list) != expected_days:
                failures.append(f"Number of items in 'days' list ({len(days_list)}) does not match expected ({expected_days})")
        else:
            failures.append("'days' is not a list")
            
        if total_days is not None:
            if total_days != expected_days:
                failures.append(f"'total_days' ({total_days}) does not match expected ({expected_days})")
                
        # Check budget_estimate
        if "budget_estimate" not in data:
            failures.append("Missing 'budget_estimate'")
        else:
            be = data["budget_estimate"]
            if not isinstance(be, dict):
                failures.append("'budget_estimate' is not an object")
                
        # Check packing_list
        if "packing_list" not in data:
            failures.append("Missing 'packing_list'")
        elif not isinstance(data["packing_list"], list):
            failures.append("'packing_list' is not a list")
            
        # Check hotel_areas
        if "hotel_areas" not in data:
            failures.append("Missing 'hotel_areas'")
        elif not isinstance(data["hotel_areas"], list):
            failures.append("'hotel_areas' is not a list")
            
        if failures:
            status = "FAIL (Invalid Schema)"
            reason = "; ".join(failures)
            if had_fences:
                reason += " (Response had markdown fences)"
            print(f"FAIL: JSON schema validation failures: {failures}")
            return {
                "id": scenario["id"],
                "query": query,
                "duration": duration,
                "status": status,
                "reason": reason,
                "is_json": True,
                "conforming": False,
                "had_fences": had_fences,
                "response_data": data
            }
        else:
            status = "PASS"
            reason = "Successfully parsed and verified JSON schema"
            if had_fences:
                status = "PASS (With Warning)"
                reason += " (Response was wrapped in markdown fences)"
            print(f"PASS: Conforming JSON response returned.")
            return {
                "id": scenario["id"],
                "query": query,
                "duration": duration,
                "status": status,
                "reason": reason,
                "is_json": True,
                "conforming": True,
                "had_fences": had_fences,
                "response_data": data
            }
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"ERROR: Exception occurred: {str(e)}")
        traceback.print_exc()
        return {
            "id": scenario["id"],
            "query": query,
            "duration": duration,
            "status": "ERROR",
            "reason": f"Unhandled exception: {str(e)}",
            "is_json": False,
            "conforming": False
        }

def main():
    results = []
    print("Starting E2E Scenario Testing...")
    for scenario in SCENARIOS:
        res = test_scenario(scenario)
        results.append(res)
        
    print("\n==========================================")
    print("TEST SUITE SUMMARY")
    print("==========================================")
    for res in results:
        print(f"Scenario {res['id']}: {res['status']}")
        print(f"  Query: {res['query']}")
        print(f"  Duration: {res['duration']:.2f}s")
        print(f"  Details: {res['reason']}")
        print("------------------------------------------")
        
    # Write summary to a JSON file for programmatic read if needed
    summary_path = os.path.join(os.path.dirname(__file__), "e2e_results.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
        
if __name__ == "__main__":
    main()
