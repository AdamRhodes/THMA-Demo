"""FastAPI application — serves synced data and triggers pipeline runs."""

import threading
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import APIKeyHeader

from config import get_settings
from api.database import fetch_all, fetch_one
from api.models import (
    AccountResponse,
    ContactResponse,
    HealthResponse,
    PipelineSummary,
    SyncStatusResponse,
    SyncTriggerResponse,
)

app = FastAPI(
    title="THMA Integration API",
    description="Serves Salesforce data synced to SQL and triggers pipeline runs.",
    version="1.0.0",
)

# ── Auth dependency ──────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(key: str = Depends(_api_key_header)) -> str:
    if key != get_settings().api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))


@app.get("/accounts", response_model=list[AccountResponse], dependencies=[Depends(verify_api_key)])
def list_accounts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    rows = fetch_all(
        "SELECT sf_id, name, industry, type, website, phone, "
        "billing_city, billing_state, annual_revenue, created_date, synced_at "
        "FROM accounts ORDER BY name LIMIT :limit OFFSET :offset"
        if get_settings().demo_mode
        else
        "SELECT sf_id, name, industry, type, website, phone, "
        "billing_city, billing_state, annual_revenue, created_date, synced_at "
        "FROM accounts ORDER BY name OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY",
        {"limit": limit, "offset": offset},
    )
    return rows


@app.get("/contacts", response_model=list[ContactResponse], dependencies=[Depends(verify_api_key)])
def list_contacts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    rows = fetch_all(
        "SELECT sf_id, account_id, first_name, last_name, email, phone, "
        "title, department, created_date, synced_at "
        "FROM contacts ORDER BY last_name LIMIT :limit OFFSET :offset"
        if get_settings().demo_mode
        else
        "SELECT sf_id, account_id, first_name, last_name, email, phone, "
        "title, department, created_date, synced_at "
        "FROM contacts ORDER BY last_name OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY",
        {"limit": limit, "offset": offset},
    )
    return rows


@app.get("/summary/pipeline", response_model=list[PipelineSummary], dependencies=[Depends(verify_api_key)])
def pipeline_summary():
    sql = (
        "SELECT stage_name, COUNT(*) AS deal_count, SUM(amount) AS total_amount, "
        "AVG(amount) AS avg_amount, AVG(probability) AS avg_probability "
        "FROM opportunities GROUP BY stage_name"
    )
    return fetch_all(sql)


@app.post("/sync/trigger", response_model=SyncTriggerResponse, dependencies=[Depends(verify_api_key)])
def trigger_sync():
    from pipeline import run as run_pipeline  # lazy import to avoid circular deps

    # Run pipeline in a background thread so the API responds immediately
    import uuid

    run_id = str(uuid.uuid4())

    def _run():
        try:
            run_pipeline(["accounts", "contacts", "opportunities"])
        except Exception:
            pass  # errors are recorded in sync_log

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return SyncTriggerResponse(run_id=run_id, status="triggered")


@app.get("/sync/status/{run_id}", response_model=SyncStatusResponse, dependencies=[Depends(verify_api_key)])
def sync_status(run_id: str):
    row = fetch_one("SELECT * FROM sync_log WHERE run_id = :run_id ORDER BY started_at DESC", {"run_id": run_id})
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("api.main:app", host=settings.api_host, port=settings.api_port, reload=True)
