from datetime import datetime, timezone

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"
STATUS_OPTIONS = ["watching", "owned", "sold"]


def _request(method: str, path: str, **kwargs: object) -> requests.Response:
    return requests.request(method, f"{API_BASE_URL}{path}", timeout=60, **kwargs)


def _load_picks(include_archived: bool = False) -> list[dict]:
    response = _request("GET", "/picks", params={"include_archived": include_archived})
    response.raise_for_status()
    picks = response.json()
    return picks if isinstance(picks, list) else []


def _load_transactions(ticker: str | None = None) -> list[dict]:
    params = {"ticker": ticker} if ticker else None
    response = _request("GET", "/transactions", params=params)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _load_latest_snapshots() -> list[dict]:
    response = _request("GET", "/snapshots/latest")
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _load_latest_prices() -> list[dict]:
    response = _request("GET", "/prices/latest")
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _safe_num(value: float | int | str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _display_num(value: float | int | str | None, precision: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.{precision}f}"


def _pct(delta: float | None) -> str:
    if delta is None:
        return "N/A"
    return f"{delta:+.2f}%"


def _calc_target_gap(current_price: float | None, target_price: float | None) -> float | None:
    if current_price is None or target_price is None or current_price == 0:
        return None
    return ((target_price - current_price) / current_price) * 100.0


def _kpi(picks: list[dict], latest_map: dict[str, dict]) -> tuple[int, int, float, float]:
    total = len(picks)
    owned = len([p for p in picks if p.get("status") == "owned"])
    confidences = []
    bullish = 0
    with_signal = 0
    for pick in picks:
        ticker = str(pick.get("ticker", "")).upper()
        analysis = latest_map.get(ticker)
        if not analysis:
            continue
        conf = analysis.get("confidence")
        if isinstance(conf, (float, int)):
            confidences.append(float(conf))
        signal = analysis.get("signal")
        if signal:
            with_signal += 1
            if signal == "BULLISH":
                bullish += 1
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    bullish_ratio = (bullish / with_signal) * 100.0 if with_signal else 0.0
    return total, owned, avg_conf, bullish_ratio


def _latest_analysis_map(analysis_response: dict | None) -> dict[str, dict]:
    if not analysis_response:
        return {}
    analyses = analysis_response.get("analyses", [])
    if not isinstance(analyses, list):
        return {}
    return {
        str(item.get("ticker", "")).upper(): item
        for item in analyses
        if isinstance(item, dict) and item.get("ticker")
    }


def _list_to_ticker_map(items: list[dict]) -> dict[str, dict]:
    return {
        str(item.get("ticker", "")).upper(): item
        for item in items
        if isinstance(item, dict) and item.get("ticker")
    }


def _run_analysis_for_tickers(tickers: list[str]) -> dict | None:
    if not tickers:
        st.warning("No active tickers available to analyze.")
        return None
    # Current API contract enforces max 5 tickers.
    if len(tickers) > 5:
        st.warning("The API currently supports up to 5 tickers per run. Please narrow the selection.")
        return None
    response = _request("POST", "/analyze", json={"watchlist": tickers})
    if response.ok:
        st.success("Analysis complete.")
        return response.json()
    detail = response.text
    try:
        detail = response.json().get("detail", detail)
    except Exception:
        pass
    st.error(f"Analysis failed: {detail}")
    return None


st.set_page_config(page_title="Financial Stock Intelligence Agent", layout="wide")
st.title("Financial Stock Intelligence Agent")
st.caption("Portfolio dashboard with saved picks, analysis snapshots, and transaction history.")

if "latest_analysis" not in st.session_state:
    st.session_state.latest_analysis = None

try:
    picks = _load_picks(include_archived=False)
except requests.RequestException as exc:
    st.error(f"Could not load picks from API: {exc}")
    st.stop()

try:
    persisted_snapshots = _load_latest_snapshots()
except requests.RequestException:
    persisted_snapshots = []

try:
    price_rows = _load_latest_prices()
except requests.RequestException:
    price_rows = []

active_picks = [p for p in picks if p.get("status") in {"watching", "owned"}]
active_tickers = [str(p.get("ticker", "")).upper() for p in active_picks if p.get("ticker")]

with st.sidebar:
    st.header("Manage Picks")
    with st.form("add_pick_form", clear_on_submit=True):
        add_ticker = st.text_input("Ticker").upper().strip()
        add_status = st.selectbox("Status", STATUS_OPTIONS, index=0)
        add_entry = st.number_input("Entry Price", min_value=0.0, value=0.0, step=0.01)
        add_target = st.number_input("Target Price", min_value=0.0, value=0.0, step=0.01)
        add_stop = st.number_input("Stop Loss", min_value=0.0, value=0.0, step=0.01)
        add_notes = st.text_area("Notes / Thesis", height=100)
        if st.form_submit_button("Add Pick"):
            payload = {
                "ticker": add_ticker,
                "status": add_status,
                "entry_price": None if add_entry == 0 else add_entry,
                "target_price": None if add_target == 0 else add_target,
                "stop_loss": None if add_stop == 0 else add_stop,
                "notes": add_notes,
            }
            try:
                resp = _request("POST", "/picks", json=payload)
                if resp.ok:
                    st.success(f"Added {add_ticker}.")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Failed to add pick."))
            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")

    st.divider()
    st.subheader("Edit Pick")
    if picks:
        pick_options = {f"{p['ticker']} (#{p['id']})": p for p in picks}
        selected_pick_label = st.selectbox("Pick", list(pick_options.keys()))
        selected_pick = pick_options[selected_pick_label]
        with st.form("edit_pick_form"):
            edit_status = st.selectbox(
                "Status",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(selected_pick["status"]),
            )
            edit_target = st.number_input(
                "Target Price",
                min_value=0.0,
                value=float(selected_pick["target_price"] or 0.0),
                step=0.01,
            )
            edit_stop = st.number_input(
                "Stop Loss",
                min_value=0.0,
                value=float(selected_pick["stop_loss"] or 0.0),
                step=0.01,
            )
            edit_entry = st.number_input(
                "Entry Price",
                min_value=0.0,
                value=float(selected_pick["entry_price"] or 0.0),
                step=0.01,
            )
            edit_notes = st.text_area("Notes / Thesis", value=selected_pick.get("notes", ""), height=100)
            save_edit = st.form_submit_button("Save Changes")
            archive_edit = st.form_submit_button("Archive Pick")
            if save_edit:
                payload = {
                    "status": edit_status,
                    "entry_price": None if edit_entry == 0 else edit_entry,
                    "target_price": None if edit_target == 0 else edit_target,
                    "stop_loss": None if edit_stop == 0 else edit_stop,
                    "notes": edit_notes,
                }
                try:
                    resp = _request("PUT", f"/picks/{selected_pick['id']}", json=payload)
                    if resp.ok:
                        st.success("Pick updated.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed to update pick."))
                except requests.RequestException as exc:
                    st.error(f"Request failed: {exc}")
            if archive_edit:
                try:
                    resp = _request("POST", f"/picks/{selected_pick['id']}/archive")
                    if resp.ok:
                        st.success("Pick archived.")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Failed to archive pick."))
                except requests.RequestException as exc:
                    st.error(f"Request failed: {exc}")
    else:
        st.info("No picks yet.")

    st.divider()
    st.subheader("Add Transaction")
    with st.form("tx_form", clear_on_submit=True):
        tx_ticker = st.text_input("Ticker ", key="tx_ticker").upper().strip()
        tx_action = st.selectbox("Action", ["buy", "sell"], index=0)
        tx_price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01)
        tx_qty = st.number_input("Quantity (optional)", min_value=0.0, value=0.0, step=1.0)
        tx_note = st.text_input("Note")
        if st.form_submit_button("Save Transaction"):
            payload = {
                "ticker": tx_ticker,
                "action": tx_action,
                "price": tx_price,
                "quantity": None if tx_qty == 0 else tx_qty,
                "date": datetime.now(timezone.utc).isoformat(),
                "note": tx_note,
            }
            try:
                resp = _request("POST", "/transactions", json=payload)
                if resp.ok:
                    st.success("Transaction saved.")
                    st.rerun()
                else:
                    st.error(resp.json().get("detail", "Failed to save transaction."))
            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")

action_col_1, action_col_2 = st.columns([2, 3])
with action_col_1:
    st.subheader("Analysis Actions")
    selected = st.multiselect("Tickers to analyze", options=active_tickers, default=active_tickers)
    if st.button("Run Analysis For Selected"):
        st.session_state.latest_analysis = _run_analysis_for_tickers(selected)
    if st.button("Refresh Prices"):
        try:
            resp = _request("POST", "/prices/refresh")
            if resp.ok:
                refreshed = resp.json().get("refreshed_count", 0)
                st.success(f"Refreshed prices for {refreshed} ticker(s).")
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Failed to refresh prices."))
        except requests.RequestException as exc:
            st.error(f"Price refresh failed: {exc}")

with action_col_2:
    st.subheader("Run Metrics")
    latest_analysis = st.session_state.latest_analysis
    if latest_analysis:
        st.write(f"Run ID: `{latest_analysis.get('run_id', 'N/A')}`")
        st.write(f"Citation Coverage Avg: {_display_num(latest_analysis.get('citation_coverage_avg'))}")
        st.write(f"Low Confidence Rate: {_display_num(latest_analysis.get('low_confidence_rate'))}")
    else:
        st.caption("Run analysis to see latest run metrics.")

analysis_map = _latest_analysis_map(st.session_state.latest_analysis)
if not analysis_map:
    analysis_map = _list_to_ticker_map(persisted_snapshots)
price_map = _list_to_ticker_map(price_rows)
total, owned, avg_conf, bullish_ratio = _kpi(picks, analysis_map)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Picks", total)
k2.metric("Owned", owned)
k3.metric("Avg Confidence", f"{avg_conf:.2f}")
k4.metric("Bullish Ratio", f"{bullish_ratio:.1f}%")

st.subheader("Portfolio")
table_rows = []
for pick in picks:
    ticker = str(pick.get("ticker", "")).upper()
    analysis = analysis_map.get(ticker, {})
    price_payload = price_map.get(ticker, {})
    signal = analysis.get("signal", "N/A")
    confidence = analysis.get("confidence")
    entry_price = _safe_num(pick.get("entry_price"))
    current_price = _safe_num(price_payload.get("price"))
    target_price = _safe_num(pick.get("target_price"))
    target_gap = _calc_target_gap(current_price, target_price)
    pnl_pct = None
    if entry_price is not None and current_price is not None and entry_price != 0:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100.0
    table_rows.append(
        {
            "Ticker": ticker,
            "Status": pick.get("status"),
            "Signal": signal,
            "Confidence": _display_num(confidence),
            "Entry": _display_num(entry_price),
            "Current": _display_num(current_price),
            "P/L %": _pct(pnl_pct),
            "Target": _display_num(target_price),
            "Stop": _display_num(pick.get("stop_loss")),
            "Target Gap %": _pct(target_gap),
            "Price As Of": price_payload.get("as_of", "N/A"),
            "Updated": pick.get("updated_at", ""),
        }
    )

if table_rows:
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
else:
    st.info("No picks saved yet. Add your first stock from the sidebar.")

st.subheader("Stock Detail")
if picks:
    detail_ticker = str(
        st.selectbox("Select ticker", options=[p["ticker"] for p in picks], key="detail_ticker")
    )
    detail_pick = next((p for p in picks if p["ticker"] == detail_ticker), None)
    detail_analysis = analysis_map.get(detail_ticker, {})
    detail_price = price_map.get(detail_ticker, {})

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f"**Ticker:** {detail_ticker}")
        if detail_pick:
            st.markdown(f"**Status:** {detail_pick.get('status', 'N/A')}")
            st.markdown(f"**Entry:** {_display_num(detail_pick.get('entry_price'))}")
            st.markdown(f"**Target:** {_display_num(detail_pick.get('target_price'))}")
            st.markdown(f"**Stop:** {_display_num(detail_pick.get('stop_loss'))}")
            st.markdown(f"**Notes:** {detail_pick.get('notes', '') or 'N/A'}")
            st.markdown(f"**Current Price:** {_display_num(detail_price.get('price'))}")
            st.markdown(f"**Price As Of:** {detail_price.get('as_of', 'N/A')}")

    with c2:
        st.markdown(f"**Signal:** {detail_analysis.get('signal', 'N/A')}")
        st.markdown(f"**Confidence:** {_display_num(detail_analysis.get('confidence'))}")
        st.markdown(f"**Summary:** {detail_analysis.get('summary', 'No analysis yet.')}")
        claims = detail_analysis.get("claims", [])
        if claims:
            st.markdown("**Top claims/citations**")
            for idx, claim in enumerate(claims[:3], start=1):
                text = claim.get("claim", "N/A")
                citations = claim.get("citations", [])
                st.write(f"{idx}. {text}")
                if citations:
                    first = citations[0]
                    title = first.get("title", "Source")
                    url = first.get("url", "")
                    st.caption(f"Source: {title} ({url})")

    try:
        tx_rows = _load_transactions(ticker=detail_ticker)
        st.markdown("**Recent Transactions**")
        if tx_rows:
            st.dataframe(
                [
                    {
                        "Action": t.get("action"),
                        "Price": _display_num(t.get("price")),
                        "Qty": _display_num(t.get("quantity")),
                        "Date": t.get("date"),
                        "Note": t.get("note", ""),
                    }
                    for t in tx_rows[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No transactions for this ticker yet.")
    except requests.RequestException as exc:
        st.error(f"Failed to load transactions: {exc}")
