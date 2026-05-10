import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from app.agents.orchestrator import run_analysis
from app.db import execute, fetch_all, fetch_one, now_iso
from app.models.schemas import (
    AnalysisSnapshotRecord,
    AnalyzeRequest,
    AnalyzeResponse,
    PriceCacheRecord,
    StockPickCreate,
    StockPickRecord,
    StockPickUpdate,
    TransactionCreate,
    TransactionRecord,
)
from app.tools.price_tool import get_price_movement

router = APIRouter()


def _save_report(response: AnalyzeResponse) -> None:
    now_utc = datetime.now(timezone.utc)
    date_dir = now_utc.strftime("%Y-%m-%d")
    report_dir = Path("reports") / date_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = now_utc.strftime("%H%M%S")
    run_file = report_dir / f"run-{timestamp}.json"
    latest_file = report_dir / "latest.json"
    payload = response.model_dump(mode="json")

    run_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save_analysis_snapshots(response: AnalyzeResponse) -> None:
    for analysis in response.analyses:
        execute(
            """
            INSERT INTO analysis_snapshots (
                ticker, run_id, signal, confidence, summary, reliability_json, claims_json, generated_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                run_id = excluded.run_id,
                signal = excluded.signal,
                confidence = excluded.confidence,
                summary = excluded.summary,
                reliability_json = excluded.reliability_json,
                claims_json = excluded.claims_json,
                generated_at = excluded.generated_at,
                updated_at = excluded.updated_at
            """,
            (
                analysis.ticker,
                response.run_id,
                analysis.signal.value,
                float(analysis.confidence),
                analysis.summary,
                json.dumps(analysis.reliability.model_dump(mode="json")),
                json.dumps([claim.model_dump(mode="json") for claim in analysis.claims]),
                analysis.generated_at.isoformat(),
                now_iso(),
            ),
        )


def _pick_row_to_record(row: sqlite3.Row | None) -> StockPickRecord:
    if row is None:
        raise HTTPException(status_code=404, detail="Stock pick not found.")
    return StockPickRecord(
        id=row["id"],
        ticker=row["ticker"],
        status=row["status"],
        entry_price=row["entry_price"],
        target_price=row["target_price"],
        stop_loss=row["stop_loss"],
        notes=row["notes"],
        archived=bool(row["archived"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _transaction_row_to_record(row: sqlite3.Row) -> TransactionRecord:
    return TransactionRecord(
        id=row["id"],
        ticker=row["ticker"],
        action=row["action"],
        price=row["price"],
        quantity=row["quantity"],
        date=datetime.fromisoformat(row["date"]),
        note=row["note"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _snapshot_row_to_record(row: sqlite3.Row) -> AnalysisSnapshotRecord:
    reliability_json = json.loads(row["reliability_json"])
    claims_json = json.loads(row["claims_json"])
    return AnalysisSnapshotRecord(
        ticker=row["ticker"],
        run_id=row["run_id"],
        signal=row["signal"],
        confidence=row["confidence"],
        summary=row["summary"],
        reliability=reliability_json,
        claims=claims_json,
        generated_at=datetime.fromisoformat(row["generated_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _price_row_to_record(row: sqlite3.Row) -> PriceCacheRecord:
    return PriceCacheRecord(
        ticker=row["ticker"],
        price=row["price"],
        change_percent=row["change_percent"],
        as_of=datetime.fromisoformat(row["as_of"]),
        source_name=row["source_name"],
        source_url=row["source_url"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_watchlist(req: AnalyzeRequest) -> AnalyzeResponse:
    watchlist = [ticker.strip().upper() for ticker in req.watchlist if ticker.strip()]
    if not watchlist:
        raise HTTPException(status_code=400, detail="Watchlist cannot be empty.")

    result = run_analysis(watchlist)
    _save_report(result)
    _save_analysis_snapshots(result)
    return result


@router.get("/picks", response_model=list[StockPickRecord])
def list_picks(include_archived: bool = False) -> list[StockPickRecord]:
    if include_archived:
        rows = fetch_all("SELECT * FROM stock_picks ORDER BY updated_at DESC")
    else:
        rows = fetch_all("SELECT * FROM stock_picks WHERE archived = 0 ORDER BY updated_at DESC")
    return [_pick_row_to_record(row) for row in rows]


@router.post("/picks", response_model=StockPickRecord, status_code=201)
def create_pick(payload: StockPickCreate) -> StockPickRecord:
    ticker = payload.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty.")

    existing = fetch_one("SELECT id FROM stock_picks WHERE ticker = ? AND archived = 0", (ticker,))
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"{ticker} already exists in active picks.")

    timestamp = now_iso()
    row_id = execute(
        """
        INSERT INTO stock_picks (
            ticker, status, entry_price, target_price, stop_loss, notes, archived, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            ticker,
            payload.status.value,
            payload.entry_price,
            payload.target_price,
            payload.stop_loss,
            payload.notes,
            timestamp,
            timestamp,
        ),
    )
    row = fetch_one("SELECT * FROM stock_picks WHERE id = ?", (row_id,))
    return _pick_row_to_record(row)


@router.put("/picks/{pick_id}", response_model=StockPickRecord)
def update_pick(pick_id: int, payload: StockPickUpdate) -> StockPickRecord:
    current = fetch_one("SELECT * FROM stock_picks WHERE id = ?", (pick_id,))
    if current is None:
        raise HTTPException(status_code=404, detail="Stock pick not found.")

    status = payload.status.value if payload.status is not None else current["status"]
    entry_price = payload.entry_price if payload.entry_price is not None else current["entry_price"]
    target_price = payload.target_price if payload.target_price is not None else current["target_price"]
    stop_loss = payload.stop_loss if payload.stop_loss is not None else current["stop_loss"]
    notes = payload.notes if payload.notes is not None else current["notes"]
    archived = int(payload.archived) if payload.archived is not None else current["archived"]

    execute(
        """
        UPDATE stock_picks
        SET status = ?, entry_price = ?, target_price = ?, stop_loss = ?, notes = ?, archived = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, entry_price, target_price, stop_loss, notes, archived, now_iso(), pick_id),
    )
    updated = fetch_one("SELECT * FROM stock_picks WHERE id = ?", (pick_id,))
    return _pick_row_to_record(updated)


@router.post("/picks/{pick_id}/archive", response_model=StockPickRecord)
def archive_pick(pick_id: int) -> StockPickRecord:
    return update_pick(pick_id, StockPickUpdate(archived=True))


@router.get("/transactions", response_model=list[TransactionRecord])
def list_transactions(ticker: str | None = None) -> list[TransactionRecord]:
    if ticker:
        rows = fetch_all(
            "SELECT * FROM transactions WHERE ticker = ? ORDER BY date DESC, id DESC",
            (ticker.strip().upper(),),
        )
    else:
        rows = fetch_all("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    return [_transaction_row_to_record(row) for row in rows]


@router.post("/transactions", response_model=TransactionRecord, status_code=201)
def create_transaction(payload: TransactionCreate) -> TransactionRecord:
    ticker = payload.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty.")

    row_id = execute(
        """
        INSERT INTO transactions (ticker, action, price, quantity, date, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticker,
            payload.action.value,
            payload.price,
            payload.quantity,
            payload.date.isoformat(),
            payload.note,
            now_iso(),
        ),
    )
    row = fetch_one("SELECT * FROM transactions WHERE id = ?", (row_id,))
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create transaction.")
    return _transaction_row_to_record(row)


@router.get("/snapshots/latest", response_model=list[AnalysisSnapshotRecord])
def list_latest_snapshots() -> list[AnalysisSnapshotRecord]:
    rows = fetch_all("SELECT * FROM analysis_snapshots ORDER BY ticker ASC")
    return [_snapshot_row_to_record(row) for row in rows]


@router.get("/prices/latest", response_model=list[PriceCacheRecord])
def list_latest_prices() -> list[PriceCacheRecord]:
    rows = fetch_all("SELECT * FROM price_cache ORDER BY ticker ASC")
    return [_price_row_to_record(row) for row in rows]


@router.post("/prices/refresh")
def refresh_prices() -> dict:
    active_rows = fetch_all(
        """
        SELECT ticker FROM stock_picks
        WHERE archived = 0 AND status IN ('watching', 'owned')
        ORDER BY ticker ASC
        """
    )
    refreshed = 0
    for row in active_rows:
        ticker = row["ticker"]
        price_data = get_price_movement(ticker)
        execute(
            """
            INSERT INTO price_cache (ticker, price, change_percent, as_of, source_name, source_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                price = excluded.price,
                change_percent = excluded.change_percent,
                as_of = excluded.as_of,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                updated_at = excluded.updated_at
            """,
            (
                str(price_data.get("ticker", ticker)).upper(),
                float(price_data.get("price", 0.0)),
                float(price_data.get("change_percent", 0.0)),
                str(price_data.get("as_of", now_iso())),
                str(price_data.get("source_name", "unknown")),
                str(price_data.get("source_url", "")),
                now_iso(),
            ),
        )
        refreshed += 1
    return {"refreshed_count": refreshed}
