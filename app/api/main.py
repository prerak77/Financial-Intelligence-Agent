from fastapi import FastAPI

from app.api.routes import router
from app.db import init_db
from app.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="Financial Stock Intelligence Agent", version="0.1.0")
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
