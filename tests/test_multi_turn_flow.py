import json
import os
import sys
import traceback
import uuid

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.travel_agent import run_agent


def main():
    session_id = str(uuid.uuid4())
    print(f"Starting multi-turn conversation test with session_id: {session_id}")

    results = []

    # -------------------------------------------------------------
    # Turn 1
    # -------------------------------------------------------------
    turn_1_prompt = "Plan 3 days in Barcelona. Focused on architecture and food. Currency EUR."
    print(f"\n--- Turn 1 Prompt: {turn_1_prompt} ---")

    try:
        t1_response = run_agent(turn_1_prompt, session_id)
        print(f"Turn 1 Response:\n{t1_response}\n")

        # Check Turn 1 response
        t1_ok = False
        t1_json = None
        if t1_response:
            t1_ok = True
            # Let's try to extract JSON if it's wrapped or returned directly
            try:
                clean_response = t1_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                t1_json = json.loads(clean_response.strip())
                print("Successfully parsed Turn 1 response as JSON.")
            except Exception as e:
                print(f"Note: Turn 1 response is not valid JSON ({e}). Checking as text.")

        # Success details for Turn 1
        results.append({
            "turn": 1,
            "prompt": turn_1_prompt,
            "response": t1_response,
            "success": t1_ok,
            "notes": "Parsed as JSON" if t1_json else "Not parsed as JSON but returned content" if t1_response else "Failed (empty response)"
        })
    except Exception as e:
        print(f"Error in Turn 1: {e}")
        traceback.print_exc()
        results.append({
            "turn": 1,
            "prompt": turn_1_prompt,
            "response": f"ERROR: {e}",
            "success": False,
            "notes": f"Exception: {e}"
        })
        return

    # Extract Day 2 weather info from Turn 1 response (if JSON) to compare in Turn 2
    day_2_weather_info = None
    if t1_json and "days" in t1_json and len(t1_json["days"]) >= 2:
        day_2_weather_info = t1_json["days"][1].get("weather")
        print(f"Day 2 weather in Turn 1 JSON: {day_2_weather_info}")

    # -------------------------------------------------------------
    # Turn 2
    # -------------------------------------------------------------
    turn_2_prompt = "What is the weather on Day 2?"
    print(f"\n--- Turn 2 Prompt: {turn_2_prompt} ---")

    try:
        t2_response = run_agent(turn_2_prompt, session_id)
        print(f"Turn 2 Response:\n{t2_response}\n")

        t2_ok = False
        t2_notes = ""
        if t2_response:
            # Check if it references weather data
            keywords = ["temp", "weather", "degree", "celsius", "rain", "sky", "cloud", "condition", "°", "c"]
            contains_keywords = any(kw in t2_response.lower() for kw in keywords)

            ref_match = False
            if day_2_weather_info:
                cond = str(day_2_weather_info.get("condition", "")).lower()
                max_t = str(day_2_weather_info.get("max_temp_c", ""))
                min_t = str(day_2_weather_info.get("min_temp_c", ""))

                cond_match = cond and cond in t2_response.lower()
                temp_match = (max_t and max_t in t2_response) or (min_t and min_t in t2_response)
                if cond_match or temp_match:
                    ref_match = True
                    t2_notes = f"Matches Turn 1 Day 2 weather values (cond: {cond_match}, temp: {temp_match})"

            if contains_keywords or ref_match:
                t2_ok = True
                if not t2_notes:
                    t2_notes = "Contains general weather keywords"
            else:
                t2_notes = "Did not match weather keywords or values"
        else:
            t2_notes = "Empty response"

        results.append({
            "turn": 2,
            "prompt": turn_2_prompt,
            "response": t2_response,
            "success": t2_ok,
            "notes": t2_notes
        })
    except Exception as e:
        print(f"Error in Turn 2: {e}")
        traceback.print_exc()
        results.append({
            "turn": 2,
            "prompt": turn_2_prompt,
            "response": f"ERROR: {e}",
            "success": False,
            "notes": f"Exception: {e}"
        })

    # -------------------------------------------------------------
    # Turn 3
    # -------------------------------------------------------------
    turn_3_prompt = "Add a Spanish restaurant to Day 1 evening."
    print(f"\n--- Turn 3 Prompt: {turn_3_prompt} ---")

    try:
        t3_response = run_agent(turn_3_prompt, session_id)
        print(f"Turn 3 Response:\n{t3_response}\n")

        t3_ok = False
        t3_notes = ""
        if t3_response:
            keywords = ["restaurant", "tapas", "paella", "dinner", "evening", "food", "dining", "barcelona", "spanish", "cuisine"]
            contains_keywords = any(kw in t3_response.lower() for kw in keywords)

            # Let's try parsing as JSON
            t3_json = None
            try:
                clean_response = t3_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                t3_json = json.loads(clean_response.strip())
            except json.JSONDecodeError:
                pass

            if t3_json:
                found_restaurant = False
                if "days" in t3_json and len(t3_json["days"]) >= 1:
                    day_1_places = t3_json["days"][0].get("places", [])
                    for place in day_1_places:
                        p_type = str(place.get("type", "")).lower()
                        p_name = str(place.get("name", "")).lower()
                        p_cuisine = str(place.get("cuisine", "")).lower()
                        if "restaurant" in p_type or "food" in p_type or "restaurant" in p_name or "spanish" in p_cuisine:
                            found_restaurant = True
                            t3_notes = f"Found restaurant '{place.get('name')}' in Day 1 of JSON itinerary."
                            break
                if found_restaurant:
                    t3_ok = True
                else:
                    t3_notes = "Parsed as JSON but couldn't find a restaurant in Day 1."
            else:
                if contains_keywords:
                    t3_ok = True
                    t3_notes = "Contains dining/restaurant keywords in text response."
                else:
                    t3_notes = "Does not mention restaurant/dining keywords."
        else:
            t3_notes = "Empty response"

        results.append({
            "turn": 3,
            "prompt": turn_3_prompt,
            "response": t3_response,
            "success": t3_ok,
            "notes": t3_notes
        })
    except Exception as e:
        print(f"Error in Turn 3: {e}")
        traceback.print_exc()
        results.append({
            "turn": 3,
            "prompt": turn_3_prompt,
            "response": f"ERROR: {e}",
            "success": False,
            "notes": f"Exception: {e}"
        })

    # -------------------------------------------------------------
    # Turn 4
    # -------------------------------------------------------------
    turn_4_prompt = "Can you change the budget currency to USD?"
    print(f"\n--- Turn 4 Prompt: {turn_4_prompt} ---")

    try:
        t4_response = run_agent(turn_4_prompt, session_id)
        print(f"Turn 4 Response:\n{t4_response}\n")

        t4_ok = False
        t4_notes = ""
        if t4_response:
            keywords = ["usd", "$", "dollar", "us dollar"]
            contains_keywords = any(kw in t4_response.lower() for kw in keywords)

            # Let's try parsing as JSON
            t4_json = None
            try:
                clean_response = t4_response.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]
                t4_json = json.loads(clean_response.strip())
            except json.JSONDecodeError:
                pass

            if t4_json:
                budget = t4_json.get("budget_estimate", {})
                curr = str(budget.get("currency", "")).upper()
                if curr == "USD":
                    t4_ok = True
                    t4_notes = "Budget currency set to USD in JSON."
                else:
                    t4_notes = f"Parsed as JSON but budget currency was {curr} instead of USD."
            else:
                if contains_keywords:
                    t4_ok = True
                    t4_notes = "Text response references USD/$."
                else:
                    t4_notes = "Does not mention USD/$."
        else:
            t4_notes = "Empty response"

        results.append({
            "turn": 4,
            "prompt": turn_4_prompt,
            "response": t4_response,
            "success": t4_ok,
            "notes": t4_notes
        })
    except Exception as e:
        print(f"Error in Turn 4: {e}")
        traceback.print_exc()
        results.append({
            "turn": 4,
            "prompt": turn_4_prompt,
            "response": f"ERROR: {e}",
            "success": False,
            "notes": f"Exception: {e}"
        })

    # Print summary
    print("\n=============================================")
    print("Multi-Turn Conversation Test Summary")
    print("=============================================")
    all_success = True
    for res in results:
        status_str = "SUCCESS" if res["success"] else "FAILED"
        if not res["success"]:
            all_success = False
        print(f"Turn {res['turn']}: {res['prompt']}")
        print(f"  Status: {status_str}")
        print(f"  Notes:  {res['notes']}")
        print("-" * 45)

    if all_success:
        print("ALL TURNS PASSED")
    else:
        print("SOME TURNS FAILED")

if __name__ == "__main__":
    main()
