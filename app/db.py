import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("data") / "portfolio.db"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL NULL,
                target_price REAL NULL,
                stop_loss REAL NULL,
                notes TEXT NOT NULL DEFAULT '',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NULL,
                date TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_snapshots (
                ticker TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                summary TEXT NOT NULL,
                reliability_json TEXT NOT NULL,
                claims_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT PRIMARY KEY,
                price REAL NOT NULL,
                change_percent REAL NOT NULL,
                as_of TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with _connect() as conn:
        return list(conn.execute(query, params).fetchall())


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(query, params).fetchone()


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    with _connect() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return int(cursor.lastrowid)


def now_iso() -> str:
    return _utc_iso()
