from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Financial Stock Intelligence Agent", version="0.1.0")
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
