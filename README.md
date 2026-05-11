# Financial Stock Intelligence Agent

Financial Stock Intelligence Agent is a single-user investing workspace built on FastAPI + Streamlit.
It combines:
- persistent stock picks and transaction tracking
- AI analysis with evidence-backed per-ticker signals
- dashboard visuals for portfolio health (instead of raw JSON-only output)

The project is built to be explainable by design:
- each output includes structured claims
- each claim is expected to include citations
- reliability and confidence are computed in a deterministic way

## What It Does

Given active picks (for example `AAPL`, `MSFT`, `NVDA`), the system:
- stores your picks in SQLite (`watching`, `owned`, `sold`)
- stores notes, entry/target/stop values, and timestamps
- records buy/sell transaction history
- runs AI analysis for selected tickers (up to 5 per run with current API contract)
- stores latest per-ticker analysis snapshots in DB
- stores latest per-ticker prices in DB cache
- renders a dashboard with KPIs, portfolio table, detail view, and recent transactions

Sample analysis request:

```json
{"watchlist": ["AAPL", "MSFT", "NVDA"]}
```

Analysis signal outputs per ticker:
  - `BULLISH`
  - `BEARISH`
  - `MIXED_SIGNAL`
  - `INSUFFICIENT_EVIDENCE`

## Architecture Overview

Core components:
- `app/api/` FastAPI app and routes for analysis, picks, transactions, snapshots, prices
- `app/agents/` orchestration, claim generation, and reliability logic
- `app/tools/` data connector layer for price, news, and SEC inputs
- `app/models/` Pydantic schemas for API contracts
- `app/db.py` SQLite initialization and query helpers
- `app/scheduler.py` APScheduler background price refresh (15 min, market hours)
- `app/ui/` Streamlit dashboard
- `app/rag/` scaffold for future ingestion and retrieval pipeline
- `app/eval/` scaffold for future evaluation checks

Current implementation status:
- end-to-end vertical slice is working
- tool connectors are mocked for deterministic local testing
- persistent portfolio state is implemented with SQLite
- background market-hours price refresh is implemented
- RAG and external live API integrations are scaffolded for next iterations

## API Contract

### Endpoints

- `GET /health` returns service status
- `POST /analyze` accepts an `AnalyzeRequest` and returns `AnalyzeResponse`
- `GET /picks` list picks (supports `include_archived`)
- `POST /picks` create a pick
- `PUT /picks/{pick_id}` update a pick
- `POST /picks/{pick_id}/archive` soft-delete (archive) a pick
- `GET /transactions` list transactions (optional `ticker` filter)
- `POST /transactions` create a transaction
- `GET /snapshots/latest` latest per-ticker analysis snapshots from DB
- `GET /prices/latest` latest per-ticker cached prices from DB
- `POST /prices/refresh` manual price refresh for active picks

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

## Persistence Model

Data is persisted in:
- SQLite DB at `data/portfolio.db`
- JSON analysis run artifacts under `reports/YYYY-MM-DD/`

SQLite tables:
- `stock_picks`
- `transactions`
- `analysis_snapshots`
- `price_cache`

### Report Output

Each analysis run is also written to:

- `reports/YYYY-MM-DD/run-HHMMSS.json`
- `reports/YYYY-MM-DD/latest.json`

This keeps a history of runs and a stable pointer to the most recent output.

## Streamlit UI Features

- KPI row: total picks, owned picks, average confidence, bullish ratio
- Portfolio table: ticker, status, signal, confidence, entry/current, P/L %, target gap
- Pick management:
  - add pick
  - edit status/entry/target/stop/notes
  - archive pick (soft delete)
- Analysis actions:
  - run analysis for selected active tickers
  - view run-level metrics
- Transactions:
  - add buy/sell transactions
  - view recent transactions by ticker
- Price actions:
  - manual refresh button
  - background refresh every 15 minutes during US market hours

## UI Preview

Dashboard overview:

![Dashboard overview](https://github.com/prerak77/Financial-Intelligence-Agent/blob/main/assests/image.png)

Stock detail panel:

![Stock detail panel](https://github.com/prerak77/Financial-Intelligence-Agent/blob/main/assests/image2.png)

## Run Locally

Your current project setup uses a Linux-style virtual environment (`.venv/bin`), so run via WSL:

1. Open terminal and enter WSL:
   - `wsl`
2. Go to project:
   - `cd /mnt/c/Users/prera/OneDrive/Desktop/financial-stock-intel-agent`
3. Activate venv:
   - `source .venv/bin/activate`
4. Install dependencies (if needed):
   - `pip install -r requirements.txt`
5. Start API:
   - `uvicorn app.api.main:app --reload`
6. In a second terminal, start UI:
   - `wsl`
   - `cd /mnt/c/Users/prera/OneDrive/Desktop/financial-stock-intel-agent`
   - `source .venv/bin/activate`
   - `streamlit run app/ui/streamlit_app.py`

Open:
- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:8501`

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
- SQLite (built-in `sqlite3`)
- APScheduler
- HTTP client integrations via `httpx`/`requests`
- Planned vector support via `chromadb`

## Roadmap

Planned next steps:
- replace mocked tools with live market/news/filing providers
- persist full analysis history (not just latest per ticker snapshot)
- add richer visual styling (badges/colors/sparklines)
- improve batch failure/retry visibility in UI
- add multi-user auth when needed
- complete RAG ingest and retrieval workflow
