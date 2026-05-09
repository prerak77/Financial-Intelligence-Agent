from datetime import datetime, timezone

from app.models.schemas import ClaimSentiment, Reliability, Signal


def assess_reliability_and_signal(claims: list, generated_at: datetime) -> tuple[Signal, float, Reliability]:
    warnings: list[str] = []
    total_claims = len(claims)
    cited_claims = sum(1 for claim in claims if len(claim.citations) > 0)
    citation_coverage = (cited_claims / total_claims) if total_claims else 0.0

    if total_claims == 0:
        return (
            Signal.INSUFFICIENT_EVIDENCE,
            0.0,
            Reliability(
                citation_coverage=0.0,
                source_conflict=False,
                freshness_hours_max=0.0,
                warnings=["No claims generated."],
            ),
        )

    if citation_coverage < 1.0:
        return (
            Signal.INSUFFICIENT_EVIDENCE,
            0.2,
            Reliability(
                citation_coverage=citation_coverage,
                source_conflict=False,
                freshness_hours_max=0.0,
                warnings=["At least one claim is missing citations."],
            ),
        )

    sentiment_map = {
        ClaimSentiment.POSITIVE: 1,
        ClaimSentiment.NEGATIVE: -1,
        ClaimSentiment.NEUTRAL: 0,
    }
    score = sum(sentiment_map[claim.sentiment] for claim in claims) / total_claims
    source_conflict = any(claim.sentiment == ClaimSentiment.POSITIVE for claim in claims) and any(
        claim.sentiment == ClaimSentiment.NEGATIVE for claim in claims
    )

    now = datetime.now(timezone.utc)
    oldest_hours = 0.0
    for claim in claims:
        for citation in claim.citations:
            age_hours = (now - citation.published_at).total_seconds() / 3600.0
            oldest_hours = max(oldest_hours, age_hours)

    if source_conflict:
        signal = Signal.MIXED_SIGNAL
        warnings.append("Conflicting positive and negative evidence across sources.")
    elif score >= 0.25:
        signal = Signal.BULLISH
    elif score <= -0.25:
        signal = Signal.BEARISH
    else:
        signal = Signal.MIXED_SIGNAL

    freshness_penalty = min(oldest_hours / 72.0, 0.5)
    confidence = max(0.1, min(1.0, 0.95 - freshness_penalty - (0.2 if source_conflict else 0.0)))

    reliability = Reliability(
        citation_coverage=citation_coverage,
        source_conflict=source_conflict,
        freshness_hours_max=round(oldest_hours, 2),
        warnings=warnings,
    )
    return signal, round(confidence, 2), reliability
