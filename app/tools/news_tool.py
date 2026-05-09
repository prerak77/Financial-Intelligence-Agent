from datetime import datetime, timedelta, timezone


def get_recent_news(ticker: str, limit: int = 10) -> list[dict]:
    """Mocked news results from the last 24h."""
    now = datetime.now(timezone.utc)
    article_time = now - timedelta(hours=2)
    return [
        {
            "ticker": ticker.upper(),
            "title": f"{ticker.upper()} announces product updates",
            "url": f"https://example.com/news/{ticker.upper()}-product-updates",
            "published_at": article_time.isoformat(),
            "retrieved_at": now.isoformat(),
            "summary": "Company announced updates that may support near-term sentiment.",
        }
    ][:limit]
