from functools import lru_cache

import httpx

_BASE = "https://countriesnow.space/api/v0.1/countries"


def _iso2_to_flag(iso2: str) -> str:
    return "".join(chr(0x1F1E0 + ord(c) - ord("A")) for c in iso2.upper())


@lru_cache(maxsize=1)
def _all_capitals() -> list[dict]:
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        r = c.get(f"{_BASE}/capital")
        r.raise_for_status()
        return r.json().get("data", [])


@lru_cache(maxsize=1)
def _all_currencies() -> list[dict]:
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        r = c.get(f"{_BASE}/currency")
        r.raise_for_status()
        return r.json().get("data", [])


@lru_cache(maxsize=64)
def get_country_info(country_name: str) -> dict:
    """Get metadata about a destination country.

    Args:
        country_name: Country name e.g. 'France', 'Japan', 'United States'.

    Returns:
        dict with name, capital, currency, flag emoji. status='error' on failure.
    """
    name_lower = country_name.lower()
    try:
        cap_entry = next(
            (c for c in _all_capitals() if c["name"].lower() == name_lower), None
        )
        cur_entry = next(
            (c for c in _all_currencies() if c["name"].lower() == name_lower), None
        )
        if not cap_entry:
            return {"status": "error", "message": f"Country '{country_name}' not found."}
        iso2 = cap_entry.get("iso2", "")
        return {
            "status": "ok",
            "name": cap_entry["name"],
            "capital": cap_entry.get("capital", ""),
            "currency": [cur_entry["currency"]] if cur_entry else [],
            "languages": [],
            "timezones": [],
            "flag": _iso2_to_flag(iso2) if iso2 else "",
            "population": 0,
        }
    except Exception as exc:
        return {"status": "error", "message": f"Country API error: {exc}"}
