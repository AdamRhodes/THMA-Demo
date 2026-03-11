import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import get_settings

logger = logging.getLogger(__name__)

# T-SQL MERGE template — parameterised per table at runtime
_MERGE_TEMPLATE = """
MERGE INTO {table} AS target
USING (SELECT :sf_id AS sf_id) AS source
ON target.sf_id = source.sf_id
WHEN MATCHED THEN
    UPDATE SET {update_cols}
WHEN NOT MATCHED THEN
    INSERT ({insert_cols})
    VALUES ({insert_vals});
"""


class DatabaseLoader:
    """Loads DataFrames into a SQL database using upsert semantics."""

    def __init__(self, engine: Engine | None = None) -> None:
        if engine is not None:
            self._engine = engine
        else:
            settings = get_settings()
            url = settings.database_url
            logger.info("Connecting to database (%s)…", "SQLite demo" if settings.demo_mode else "Azure SQL")
            self._engine = create_engine(url, echo=False)
        self._demo = get_settings().demo_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert(self, table: str, df: pd.DataFrame, key_column: str = "sf_id") -> int:
        if df.empty:
            logger.warning("upsert(%s): empty DataFrame — nothing to load.", table)
            return 0

        if self._demo:
            return self._upsert_sqlite(table, df, key_column)
        return self._upsert_mssql(table, df, key_column)

    def log_sync(
        self,
        run_id: str,
        status: str,
        records_extracted: int = 0,
        records_loaded: int = 0,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._engine.begin() as conn:
            if self._demo:
                conn.execute(
                    text(
                        "INSERT INTO sync_log (run_id, status, started_at, completed_at, "
                        "records_extracted, records_loaded, error_message) "
                        "VALUES (:run_id, :status, :started, :completed, :extracted, :loaded, :error)"
                    ),
                    {
                        "run_id": run_id,
                        "status": status,
                        "started": now,
                        "completed": now if status != "running" else None,
                        "extracted": records_extracted,
                        "loaded": records_loaded,
                        "error": error_message,
                    },
                )
            else:
                conn.execute(
                    text(
                        "INSERT INTO sync_log (run_id, status, records_extracted, "
                        "records_loaded, error_message) "
                        "VALUES (:run_id, :status, :extracted, :loaded, :error)"
                    ),
                    {
                        "run_id": run_id,
                        "status": status,
                        "extracted": records_extracted,
                        "loaded": records_loaded,
                        "error": error_message,
                    },
                )
        logger.info("sync_log: run_id=%s status=%s", run_id, status)

    def ensure_demo_tables(self) -> None:
        """Create tables in SQLite for demo mode (no-op for Azure SQL)."""
        if not self._demo:
            return
        ddl = [
            """CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                industry TEXT, type TEXT, website TEXT, phone TEXT,
                billing_city TEXT, billing_state TEXT,
                annual_revenue REAL, created_date TEXT,
                synced_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_id TEXT UNIQUE NOT NULL,
                account_id TEXT,
                first_name TEXT, last_name TEXT NOT NULL,
                email TEXT, phone TEXT, title TEXT, department TEXT,
                created_date TEXT, synced_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sf_id TEXT UNIQUE NOT NULL,
                account_id TEXT,
                name TEXT NOT NULL,
                stage_name TEXT, amount REAL, close_date TEXT,
                probability REAL, created_date TEXT,
                synced_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                records_extracted INTEGER,
                records_loaded INTEGER,
                error_message TEXT
            )""",
        ]
        with self._engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))
        logger.info("Demo SQLite tables ensured.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upsert_mssql(self, table: str, df: pd.DataFrame, key_column: str) -> int:
        cols = [c for c in df.columns if c != key_column]
        update_clause = ", ".join(f"{c} = :{c}" for c in cols)
        insert_cols = ", ".join([key_column] + cols)
        insert_vals = ", ".join(f":{c}" for c in [key_column] + cols)

        merge_sql = _MERGE_TEMPLATE.format(
            table=table,
            update_cols=update_clause,
            insert_cols=insert_cols,
            insert_vals=insert_vals,
        )

        loaded = 0
        with self._engine.begin() as conn:
            for row in df.to_dict(orient="records"):
                # Convert pandas Timestamps to Python datetime for pyodbc
                params = {}
                for k, v in row.items():
                    if isinstance(v, pd.Timestamp):
                        params[k] = v.to_pydatetime()
                    elif isinstance(v, float) and pd.isna(v):
                        params[k] = None
                    else:
                        params[k] = v         
                              
                conn.execute(text(merge_sql), params)
                loaded += 1

        logger.info("upsert(%s): %d records merged into Azure SQL.", table, loaded)
        return loaded

    def _upsert_sqlite(self, table: str, df: pd.DataFrame, key_column: str) -> int:
        cols = list(df.columns)
        placeholders = ", ".join(f":{c}" for c in cols)
        col_list = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"

        loaded = 0
        with self._engine.begin() as conn:
            for row in df.to_dict(orient="records"):
                params: dict[str, Any] = {}
                for k, v in row.items():
                    if isinstance(v, pd.Timestamp):
                        params[k] = v.isoformat()
                    else:
                        params[k] = v
                conn.execute(text(sql), params)
                loaded += 1

        logger.info("upsert(%s): %d records inserted/replaced into SQLite.", table, loaded)
        return loaded
