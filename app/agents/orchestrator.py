import time
from datetime import datetime, timezone
from uuid import uuid4

from app.agents.analyzer import generate_claims_from_context
from app.agents.reliability_checker import assess_reliability_and_signal
from app.models.schemas import AnalyzeResponse, StockAnalysis
from app.tools.news_tool import get_recent_news
from app.tools.price_tool import get_price_movement
from app.tools.sec_tool import get_recent_sec_filings


def run_analysis(watchlist: list[str]) -> AnalyzeResponse:
    run_id = str(uuid4())
    generated_at = datetime.now(timezone.utc)
    analyses: list[StockAnalysis] = []
    runtime_start = time.perf_counter()

    for ticker in watchlist:
        clean_ticker = ticker.strip().upper()
        price_data = get_price_movement(clean_ticker)
        news_items = get_recent_news(clean_ticker, limit=10)
        sec_items = get_recent_sec_filings(clean_ticker, limit=5)

        claims = generate_claims_from_context(price_data, news_items, sec_items)
        signal, confidence, reliability = assess_reliability_and_signal(claims, generated_at)

        summary = (
            f"{clean_ticker} analysis based on latest price movement, recent news, and SEC metadata. "
            f"Signal is {signal.value} with confidence {confidence:.2f}."
        )
        analyses.append(
            StockAnalysis(
                run_id=run_id,
                generated_at=generated_at,
                ticker=clean_ticker,
                signal=signal,
                confidence=confidence,
                summary=summary,
                claims=claims,
                reliability=reliability,
            )
        )

    elapsed = time.perf_counter() - runtime_start
    low_conf_count = sum(1 for a in analyses if a.confidence < 0.5)
    citation_cov_avg = sum(a.reliability.citation_coverage for a in analyses) / len(analyses) if analyses else 0.0

    return AnalyzeResponse(
        run_id=run_id,
        generated_at=generated_at,
        analyses=analyses,
        citation_coverage_avg=round(citation_cov_avg, 2),
        low_confidence_rate=round(low_conf_count / len(analyses), 2) if analyses else 0.0,
        avg_runtime_per_ticker=round(elapsed / len(analyses), 3) if analyses else 0.0,
        failure_recovery_rate=1.0,  # mocked: replace when retries/tool failure tracking is wired
    )
