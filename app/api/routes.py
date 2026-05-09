import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import run_analysis
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter()


def _save_report(response: AnalyzeResponse) -> None:
    date_dir = datetime.utcnow().strftime("%Y-%m-%d")
    report_dir = Path("reports") / date_dir
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%H%M%S")
    run_file = report_dir / f"run-{timestamp}.json"
    latest_file = report_dir / "latest.json"
    payload = response.model_dump(mode="json")

    run_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_watchlist(req: AnalyzeRequest) -> AnalyzeResponse:
    watchlist = [ticker.strip().upper() for ticker in req.watchlist if ticker.strip()]
    if not watchlist:
        raise HTTPException(status_code=400, detail="Watchlist cannot be empty.")

    result = run_analysis(watchlist)
    _save_report(result)
    return result
