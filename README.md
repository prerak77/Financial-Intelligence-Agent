# Financial Stock Intelligence Agent

Financial Stock Intelligence Agent is an agent that analyzes a stock watchlist and returns evidence-backed per-ticker signals.

The project is built to be explainable by design:
- each output includes structured claims
- each claim is expected to include citations
- reliability and confidence are computed in a deterministic way

## What It Does

Given a request like:

```json
{"watchlist": ["AAPL", "MSFT", "NVDA"]}
```

the system:
- validates and normalizes the tickers
- gathers context from price, news, and SEC filing tools
- generates claim-level evidence
- scores reliability and confidence
- returns one of these signals per ticker:
  - `BULLISH`
  - `BEARISH`
  - `MIXED_SIGNAL`
  - `INSUFFICIENT_EVIDENCE`
- saves a timestamped report to disk

## Architecture Overview

Core components:
- `app/api/` FastAPI app and routes (`/health`, `/analyze`)
- `app/agents/` orchestration, claim generation, and reliability logic
- `app/tools/` data connector layer for price, news, and SEC inputs
- `app/models/` Pydantic schemas for request and response contracts
- `app/ui/` Streamlit UI client that calls the API
- `app/rag/` scaffold for future ingestion and retrieval pipeline
- `app/eval/` scaffold for future evaluation checks

Current implementation status:
- end-to-end vertical slice is working
- tool connectors are mocked for deterministic local testing
- RAG and external API integrations are scaffolded for next iterations

## API Contract

### Endpoints

- `GET /health` returns service status
- `POST /analyze` accepts an `AnalyzeRequest` and returns `AnalyzeResponse`

### Request rules

- `watchlist` must contain between 1 and 5 tickers
- tickers are normalized to uppercase
- empty values are rejected

### Response includes

- per-ticker analysis with summary, claims, reliability, and confidence
- run-level metrics:
  - `citation_coverage_avg`
  - `low_confidence_rate`
  - `avg_runtime_per_ticker`
  - `failure_recovery_rate`

## Report Output

Each analysis run is persisted under:

- `reports/YYYY-MM-DD/run-HHMMSS.json`
- `reports/YYYY-MM-DD/latest.json`

This keeps a history of runs and a stable pointer to the most recent output.

## Run Locally

1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add credentials if needed.
4. Start the API:
   - `uvicorn app.api.main:app --reload`
5. Optional: run the Streamlit UI in another terminal:
   - `streamlit run app/ui/streamlit_app.py`
6. Call the API:
   - `POST http://localhost:8000/analyze`
   - body: `{"watchlist":["AAPL","MSFT","NVDA"]}`

## Quick Curl Test

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"watchlist\":[\"AAPL\",\"MSFT\",\"NVDA\"]}"
```

## Tech Stack

- Python
- FastAPI
- Pydantic
- Uvicorn
- Streamlit
- HTTP client integrations via `httpx`/`requests`
- Planned vector and scheduling support via `chromadb` and `apscheduler`

## Roadmap

Planned next steps:
- replace mocked tools with live market/news/filing APIs
- implement retry and failure accounting in tool calls
- complete RAG ingest and retrieval workflow
- add richer UI cards for signal, confidence, and evidence
