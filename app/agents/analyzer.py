from datetime import datetime

from app.models.schemas import Citation, Claim, ClaimSentiment, SourceType


def generate_claims_from_context(price_data: dict, news_items: list[dict], sec_items: list[dict]) -> list[Claim]:
    claims: list[Claim] = []

    # Claim from price movement
    claims.append(
        Claim(
            claim=f"{price_data['ticker']} moved {price_data['change_percent']:.2f}% in the latest session.",
            sentiment=ClaimSentiment.POSITIVE if price_data["change_percent"] > 0 else ClaimSentiment.NEGATIVE,
            citations=[
                Citation(
                    source_type=SourceType.PRICE,
                    title=f"{price_data['ticker']} latest price snapshot",
                    url=price_data["source_url"],
                    published_at=datetime.fromisoformat(price_data["as_of"]),
                    retrieved_at=datetime.fromisoformat(price_data["as_of"]),
                )
            ],
        )
    )

    if news_items:
        top_news = news_items[0]
        claims.append(
            Claim(
                claim=f"Recent coverage: {top_news['title']}.",
                sentiment=ClaimSentiment.NEUTRAL,
                citations=[
                    Citation(
                        source_type=SourceType.NEWS,
                        title=top_news["title"],
                        url=top_news["url"],
                        published_at=datetime.fromisoformat(top_news["published_at"]),
                        retrieved_at=datetime.fromisoformat(top_news["retrieved_at"]),
                    )
                ],
            )
        )

    if sec_items:
        top_filing = sec_items[0]
        claims.append(
            Claim(
                claim=f"Latest filing context includes form {top_filing['form']} submitted recently.",
                sentiment=ClaimSentiment.NEUTRAL,
                citations=[
                    Citation(
                        source_type=SourceType.SEC_FILING,
                        title=top_filing["headline"],
                        url=top_filing["url"],
                        published_at=datetime.fromisoformat(top_filing["filed_at"]),
                        retrieved_at=datetime.fromisoformat(top_filing["retrieved_at"]),
                    )
                ],
            )
        )

    return claims
