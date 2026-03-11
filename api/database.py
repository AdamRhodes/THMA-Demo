from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, echo=False)
    return _engine


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    """Execute a read query and return rows as dicts."""
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
