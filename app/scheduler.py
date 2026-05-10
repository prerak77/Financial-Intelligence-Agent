from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import execute, fetch_all, now_iso
from app.tools.price_tool import get_price_movement

EASTERN_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

scheduler = BackgroundScheduler(timezone=EASTERN_TZ)


def _is_market_hours(now_est: datetime) -> bool:
    if now_est.weekday() >= 5:
        return False
    local_time = now_est.time()
    return MARKET_OPEN <= local_time <= MARKET_CLOSE


def refresh_price_cache() -> int:
    now_est = datetime.now(EASTERN_TZ)
    if not _is_market_hours(now_est):
        return 0

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
    return refreshed


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        refresh_price_cache,
        trigger="interval",
        minutes=15,
        id="price-refresh-15m",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
