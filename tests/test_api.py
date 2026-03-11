"""API endpoint tests — uses demo mode (SQLite) so no Azure SQL needed."""

import os

# Force demo mode before any app imports
os.environ["DEMO_MODE"] = "true"
os.environ["API_KEY"] = "test-key-123"

import pytest
from fastapi.testclient import TestClient

from api.main import app
from etl.load import DatabaseLoader


@pytest.fixture(autouse=True)
def _setup_demo_db(tmp_path, monkeypatch):
    """Point demo DB to a temp file and create tables."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DEMO_MODE", "true")

    # Patch the database_url so both loader and API use the same temp DB
    from config import Settings, get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("API_KEY", "test-key-123")

    # Override the database URL via a fresh Settings instance
    original_prop = Settings.database_url.fget

    def _temp_db_url(self):
        return f"sqlite:///{db_path}"

    monkeypatch.setattr(Settings, "database_url", property(_temp_db_url))
    get_settings.cache_clear()

    # Reset cached engine in api.database
    import api.database as db_mod
    db_mod._engine = None

    loader = DatabaseLoader()
    loader.ensure_demo_tables()

    # Seed a couple of rows
    import pandas as pd
    from datetime import datetime, timezone

    accounts_df = pd.DataFrame([{
        "sf_id": "001X",
        "name": "Test Hospital",
        "industry": "Healthcare",
        "type": "Customer",
        "website": None,
        "phone": "555-9999",
        "billing_city": "Arlington",
        "billing_state": "VA",
        "annual_revenue": 1000000,
        "created_date": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }])
    loader.upsert("accounts", accounts_df)

    yield

    # Cleanup
    monkeypatch.setattr(Settings, "database_url", property(original_prop))
    get_settings.cache_clear()
    db_mod._engine = None


@pytest.fixture
def client():
    return TestClient(app)


HEADERS = {"X-API-Key": "test-key-123"}


class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "timestamp" in body


class TestAuth:
    def test_missing_key_returns_401_or_403(self, client):
        resp = client.get("/accounts")
        assert resp.status_code in (401, 403)

    def test_wrong_key_returns_403(self, client):
        resp = client.get("/accounts", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 403

    def test_valid_key_passes(self, client):
        resp = client.get("/accounts", headers=HEADERS)
        assert resp.status_code == 200


class TestAccounts:
    def test_returns_seeded_data(self, client):
        resp = client.get("/accounts", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["sf_id"] == "001X"
        assert data[0]["name"] == "Test Hospital"


class TestPipelineSummary:
    def test_returns_list(self, client):
        resp = client.get("/summary/pipeline", headers=HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestSyncStatus:
    def test_not_found(self, client):
        resp = client.get("/sync/status/00000000-0000-0000-0000-000000000000", headers=HEADERS)
        assert resp.status_code == 404
