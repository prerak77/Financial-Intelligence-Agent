from datetime import datetime, timedelta, timezone


def get_recent_sec_filings(ticker: str, limit: int = 5) -> list[dict]:
    """Mocked SEC filings metadata; replace with EDGAR submissions query next."""
    now = datetime.now(timezone.utc)
    filing_time = now - timedelta(days=7)
    return [
        {
            "ticker": ticker.upper(),
            "form": "8-K",
            "headline": f"{ticker.upper()} files latest 8-K update",
            "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker.upper()}",
            "filed_at": filing_time.isoformat(),
            "retrieved_at": now.isoformat(),
        }
    ][:limit]
