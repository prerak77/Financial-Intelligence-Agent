def citation_coverage(claims: list[dict]) -> float:
    if not claims:
        return 0.0
    cited = sum(1 for c in claims if c.get("citations"))
    return cited / len(claims)
