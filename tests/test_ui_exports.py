import sys
import os
import json
import tempfile

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.ui.export import plan_to_markdown, plan_to_pdf

# Generate mock travel plan matching the schema
MOCK_PLAN = {
    "destination": "Paris, France 🇫🇷",
    "total_days": 2,
    "country_info": {
        "name": "France",
        "capital": "Paris",
        "currency": ["EUR"],
        "languages": ["French"],
        "timezones": ["CET"],
        "flag": "🇫🇷"
    },
    "currency_info": {
        "from_currency": "USD",
        "to_currency": "EUR",
        "rate": 0.92,
        "date": "2026-07-09"
    },
    "days": [
        {
            "day": 1,
            "theme": "Art & Cafes in Montmartre 🎨☕",
            "weather": {
                "date": "2026-07-10",
                "max_temp_c": 24.5,
                "min_temp_c": 15.0,
                "precipitation_mm": 0.0,
                "condition": "Partly cloudy"
            },
            "places": [
                {
                    "name": "Sacré-Cœur Basilica 🏰",
                    "type": "sightseeing",
                    "lat": 48.8867,
                    "lon": 2.3431,
                    "why": "Stunning panoramic views of Paris and historical significance.",
                    "tip": "Arrive early to avoid the crowds.",
                    "opening_hours": "6am-10:30pm",
                    "cuisine": None,
                    "walk_from_prev_min": None
                },
                {
                    "name": "Café des Deux Moulins 🍿",
                    "type": "restaurant",
                    "lat": 48.8856,
                    "lon": 2.3331,
                    "why": "Famous café from the movie Amélie, great for a quick coffee.",
                    "tip": "Try the crème brûlée.",
                    "opening_hours": "7:30am-2am",
                    "cuisine": "French",
                    "walk_from_prev_min": 10
                }
            ]
        }
    ],
    "intro": "Welcome to Paris, the City of Light! 🗼 Here is your curated 1-day itinerary.",
    "bonus_tip": "Watch out for pickpockets near major tourist attractions. ⚠️",
    "budget_estimate": {
        "currency": "EUR",
        "per_day_low": 60,
        "per_day_mid": 150,
        "per_day_high": 300,
        "notes": "Covers hosteling, public transit, and dining."
    },
    "packing_list": [
        "Comfortable walking shoes 👟",
        "Light jacket 🧥",
        "Travel adapter 🔌"
    ],
    "hotel_areas": [
        {
            "name": "Montmartre",
            "why": "Romantic atmosphere and artistic history.",
            "price_range": "$$"
        }
    ]
}

def test_plan_to_markdown():
    print("Running test_plan_to_markdown...")
    markdown_output = plan_to_markdown(MOCK_PLAN)
    
    # Assert return type
    assert isinstance(markdown_output, str), "Markdown output is not a string"
    
    # Verify key itinerary strings are in the Markdown
    assert "# Paris, France" in markdown_output, "Destination title missing or incorrect"
    assert "City of Light!" in markdown_output, "Intro string missing"
    assert "Montmartre" in markdown_output, "Hotel area or day theme missing"
    assert "Sacré-Cœur" in markdown_output, "Place name missing"
    assert "Café des Deux Moulins" in markdown_output, "Restaurant name missing"
    assert "Comfortable walking shoes" in markdown_output, "Packing list item missing"
    assert "Budget Estimate (per day, EUR)" in markdown_output, "Budget header missing"
    assert "Local Tip" in markdown_output, "Local/Bonus tip header missing"
    
    # Check that emojis are preserved in markdown
    assert "🇫🇷" in markdown_output, "Emojis should be preserved in markdown"
    assert "🗼" in markdown_output, "Emojis should be preserved in markdown"
    
    print("  PASS: test_plan_to_markdown completed successfully.")

def test_plan_to_pdf():
    print("Running test_plan_to_pdf...")
    
    # Verify that plan_to_pdf generates bytes and doesn't crash on standard unicode characters (such as emojis)
    try:
        pdf_bytes = plan_to_pdf(MOCK_PLAN)
    except Exception as e:
        raise AssertionError(f"plan_to_pdf crashed with exception: {e}")
        
    assert isinstance(pdf_bytes, bytes), "PDF output is not bytes"
    assert len(pdf_bytes) > 0, "PDF output is empty"
    
    # Write to a temporary file on disk
    temp_dir = tempfile.gettempdir()
    temp_pdf_path = os.path.join(temp_dir, "test_itinerary.pdf")
    
    try:
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"  PDF successfully written to {temp_pdf_path}")
        
        # Verify that the PDF parses without errors using pypdf
        from pypdf import PdfReader
        
        reader = PdfReader(temp_pdf_path)
        assert len(reader.pages) > 0, "PDF has no pages"
        
        # Extract text to ensure it compiles/renders readable content
        first_page_text = reader.pages[0].extract_text()
        assert first_page_text, "Failed to extract text from PDF first page"
        
        # Note: Since _safe strips out non-latin-1 characters (emojis),
        # the text shouldn't contain emojis, but it should contain the safe strings.
        assert "Travel Itinerary - Paris, France" in first_page_text, "Destination missing from PDF text"
        assert "City of Light!" in first_page_text, "Intro missing from PDF text"
        assert "Montmartre" in first_page_text, "Hotel area or day theme missing from PDF text"
        
        # Verify emojis are NOT present in the PDF text (since they are stripped/ignored by _safe)
        assert "🇫🇷" not in first_page_text, "Emojis should be stripped by _safe in PDF"
        
        print("  PASS: test_plan_to_pdf completed successfully (PDF parsed and validated).")
        
    finally:
        # Clean up
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            print("  Cleaned up temporary PDF file.")

if __name__ == "__main__":
    try:
        test_plan_to_markdown()
        print("-" * 50)
        test_plan_to_pdf()
        print("-" * 50)
        print("ALL TESTS PASSED!")
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR RUNNING TESTS: {e}")
        sys.exit(1)
