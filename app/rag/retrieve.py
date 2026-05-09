def retrieve_top_k(query: str, k: int = 6) -> list[dict]:
    """Placeholder retrieval function."""
    return [{"chunk": f"Mock chunk for: {query}", "score": 0.1} for _ in range(k)]
