from datetime import datetime, timezone


def get_price_movement(ticker: str) -> dict:
    """Mocked price movement; replace with Finnhub/Polygon integration next."""
    now = datetime.now(timezone.utc)
    return {
        "ticker": ticker.upper(),
        "price": 100.0,
        "change_percent": 1.2,
        "as_of": now.isoformat(),
        "source_name": "Mock Price Feed",
        "source_url": f"https://example.com/prices/{ticker.upper()}",
    }
