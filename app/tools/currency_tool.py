import asyncio
import httpx


async def get_currency_rate(from_currency: str, to_currency: str) -> dict:
    """Get the live exchange rate between two fiat currencies.

    Use this tool when the user asks about currency conversion, how far
    their money will go, or pricing in a foreign currency.

    Args:
        from_currency: Source ISO currency code e.g. 'USD', 'GBP'.
        to_currency: Target ISO currency code e.g. 'EUR', 'JPY', 'AED'.

    Returns:
        dict with from_currency, to_currency, rate, and date.
        status='error' on failure.
    """
    def _sync():
        base = from_currency.strip().upper()
        target = to_currency.strip().upper()
        url = "https://api.frankfurter.dev/v1/latest"
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(url, params={"base": base, "symbols": target})
                r.raise_for_status()
                data = r.json()
            rate = data["rates"].get(target)
            if rate is None:
                return {"status": "error", "message": f"Currency '{target}' not found."}
            return {
                "status": "ok",
                "from_currency": base,
                "to_currency": target,
                "rate": rate,
                "date": data.get("date", ""),
            }
        except Exception as exc:
            return {"status": "error", "message": f"Currency API error: {exc}"}

    return await asyncio.to_thread(_sync)
