# MVP Spec v0.1

## Scope

- Input: watchlist tickers
- Data pulled per ticker:
  - latest price movement
  - top recent news (24h)
  - latest SEC filing headlines (if available)
- Output:
  - per-stock summary
  - signal: `BULLISH | BEARISH | MIXED_SIGNAL | INSUFFICIENT_EVIDENCE`
  - citations for every claim
  - confidence score and reliability warnings

## Locked Decisions

- Python `3.11`
- Backend `FastAPI`
- UI `Streamlit`
- RAG store `Chroma (local)`
- Scheduler `APScheduler`
- Data APIs: `Finnhub`, `NewsAPI`, `SEC EDGAR`
- LLM primary: `Gemini Flash`

## Reliability Rules

- If no strong sources: `INSUFFICIENT_EVIDENCE`
- If sources conflict: `MIXED_SIGNAL`
- Never output uncited factual claims
- Include source freshness timestamp
- Retry failed APIs with exponential backoff (3 attempts)

## Runtime Limits (MVP)

- Max tickers per run: `5`
- News items fetched per ticker: `10`
- SEC filings checked per ticker: `5`
- Retrieval top-k: `6`
- Per-ticker LLM timeout: `25s`
- Total run timeout: `120s`

## First Milestone (48h)

- Input 3 tickers
- Run analysis
- Display summary + citations + confidence
- Save to `reports/YYYY-MM-DD/run-<timestamp>.json` and `latest.json`
