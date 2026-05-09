# Process Guide: How This MVP Works

This document explains the current end-to-end flow of your Financial Stock Intelligence Agent, in simple terms.

## 1) What starts the process

You run the API and send a request to:

- `POST /analyze`
- Request body example:
  - `{"watchlist": ["AAPL", "MSFT", "NVDA"]}`

Main API entrypoint:

- `app/api/main.py` creates the FastAPI app.
- `app/api/routes.py` defines `POST /analyze`.

## 2) Request validation and normalization

Inside `app/api/routes.py`:

1. Request body is validated by `AnalyzeRequest` from `app/models/schemas.py`.
2. Tickers are cleaned (`strip()` and `upper()`).
3. Empty watchlist is rejected with HTTP 400.

So this layer protects your core logic from bad inputs.

## 3) Orchestration per ticker

In `app/agents/orchestrator.py`, `run_analysis(watchlist)` is the main coordinator.

For each ticker, it does:

1. Fetch price movement from `get_price_movement()` (`app/tools/price_tool.py`)
2. Fetch recent news from `get_recent_news()` (`app/tools/news_tool.py`)
3. Fetch SEC metadata from `get_recent_sec_filings()` (`app/tools/sec_tool.py`)
4. Build claims with citations using `generate_claims_from_context()` (`app/agents/analyzer.py`)
5. Compute signal, confidence, and reliability with `assess_reliability_and_signal()` (`app/agents/reliability_checker.py`)
6. Build a `StockAnalysis` object

After all tickers:

- it computes aggregate metrics:
  - `citation_coverage_avg`
  - `low_confidence_rate`
  - `avg_runtime_per_ticker`
  - `failure_recovery_rate` (currently mocked at `1.0`)

## 4) Tool layer behavior (current state)

Right now all tools are mocked, so the app runs without external APIs:

- `price_tool.py`: returns fixed sample price data (`change_percent = 1.2`)
- `news_tool.py`: returns one synthetic news item from ~2 hours ago
- `sec_tool.py`: returns one synthetic SEC filing metadata item from ~7 days ago

Why this is useful:

- You can test architecture and reliability logic before API integration complexity.

## 5) Analyzer behavior

In `app/agents/analyzer.py`, the analyzer converts raw tool outputs into structured claims:

- Price claim (positive if price change > 0, else negative)
- One news claim (neutral)
- One SEC claim (neutral)

Each claim includes at least one `Citation` with:

- source type (`price`, `news`, `sec_filing`)
- title
- URL
- `published_at`
- `retrieved_at`

This is the backbone for your "every claim must be cited" rule.

## 6) Reliability and signal logic

In `app/agents/reliability_checker.py`:

1. If there are zero claims -> `INSUFFICIENT_EVIDENCE`
2. If citation coverage is below 100% -> `INSUFFICIENT_EVIDENCE`
3. Otherwise compute sentiment score from claims:
   - positive = +1
   - neutral = 0
   - negative = -1
4. Detect conflict if both positive and negative claims exist
5. Signal thresholds:
   - score >= 0.25 -> `BULLISH`
   - score <= -0.25 -> `BEARISH`
   - else -> `MIXED_SIGNAL`
   - conflict overrides to `MIXED_SIGNAL`
6. Confidence is deterministic and reduced for:
   - older citations (freshness penalty)
   - source conflict

This keeps confidence explainable and reproducible.

## 7) Response schema

All outputs are enforced by Pydantic models in `app/models/schemas.py`.

Important models:

- `AnalyzeRequest`
- `Citation`
- `Claim`
- `Reliability`
- `StockAnalysis`
- `AnalyzeResponse`

This gives you a stable contract for API, UI, and report files.

## 8) Report saving

After each `/analyze` run, `app/api/routes.py` saves output to:

- `reports/YYYY-MM-DD/run-HHMMSS.json`
- `reports/YYYY-MM-DD/latest.json`

So every run is persisted and the newest run is easy to load.

## 9) UI flow

`app/ui/streamlit_app.py` does:

1. takes comma-separated tickers input
2. calls `http://localhost:8000/analyze`
3. renders returned JSON in the page

So the UI is currently a thin client over your API.

## 10) RAG and eval folders (current status)

These are scaffold placeholders:

- `app/rag/ingest.py`
- `app/rag/embed.py`
- `app/rag/retrieve.py`
- `app/eval/checks.py`

They exist so your architecture is ready for the next steps.

## 11) What is already working vs not yet implemented

Working now:

- folder architecture
- `POST /analyze` end-to-end
- citations in output
- deterministic reliability logic
- report saving
- streamlit trigger + response display

Not implemented yet:

- real Finnhub/NewsAPI/SEC API calls
- retry/backoff wrappers in tool layer
- true RAG chunk/embed/retrieve pipeline
- LLM-generated summary from retrieved context
- conflict detection from real multi-source evidence
- non-mocked `failure_recovery_rate`

## 12) Recommended next implementation order

1. Replace mocked tool calls with real API integrations (with 3-attempt backoff)
2. Add tool-failure and retry counters for `failure_recovery_rate`
3. Implement RAG ingestion + retrieval
4. Add Gemini call in analyzer using retrieved context only
5. Tighten reliability checker with explicit conflicting-source rules
6. Add UI cards (not just raw JSON) for summary/signal/confidence/warnings

---

If helpful, next I can create a second file called `runbook.md` with exact commands to run API + UI + sample curl tests.
