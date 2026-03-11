import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Maps Salesforce field names → database column names
ACCOUNT_COLUMNS = {
    "Id": "sf_id",
    "Name": "name",
    "Industry": "industry",
    "Type": "type",
    "Website": "website",
    "Phone": "phone",
    "BillingCity": "billing_city",
    "BillingState": "billing_state",
    "AnnualRevenue": "annual_revenue",
    "CreatedDate": "created_date",
}

CONTACT_COLUMNS = {
    "Id": "sf_id",
    "AccountId": "account_id",
    "FirstName": "first_name",
    "LastName": "last_name",
    "Email": "email",
    "Phone": "phone",
    "Title": "title",
    "Department": "department",
    "CreatedDate": "created_date",
}

OPPORTUNITY_COLUMNS = {
    "Id": "sf_id",
    "AccountId": "account_id",
    "Name": "name",
    "StageName": "stage_name",
    "Amount": "amount",
    "CloseDate": "close_date",
    "Probability": "probability",
    "CreatedDate": "created_date",
}


def _transform(
    records: list[dict[str, Any]],
    column_map: dict[str, str],
    object_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Generic transform: rename, dedup, parse dates, add synced_at."""
    df = pd.DataFrame(records)

    # Keep only mapped columns (drop Salesforce metadata like 'attributes')
    known_cols = [c for c in column_map if c in df.columns]
    df = df[known_cols].rename(columns=column_map)

    input_count = len(df)

    # Deduplicate on sf_id
    df = df.drop_duplicates(subset=["sf_id"], keep="last")
    dedup_count = input_count - len(df)

    # Parse date columns
    for col in df.columns:
        if col.endswith("_date"):
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    # Add sync timestamp
    df["synced_at"] = datetime.now(timezone.utc)

    # Replace NaN with None for SQL compatibility
    df = df.where(df.notna(), None)

    # Null counts for logging
    null_counts = df.isnull().sum().to_dict()

    

    stats = {
        "object": object_name,
        "input_count": input_count,
        "output_count": len(df),
        "dedup_count": dedup_count,
        "null_counts": null_counts,
    }
    logger.info("Transform [%s]: %d in → %d out (%d duplicates removed)", object_name, input_count, len(df), dedup_count)
    return df, stats


class TransformEngine:
    """Cleans and normalizes raw Salesforce records into DataFrames."""

    def transform_accounts(self, records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
        return _transform(records, ACCOUNT_COLUMNS, "accounts")

    def transform_contacts(self, records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
        return _transform(records, CONTACT_COLUMNS, "contacts")

    def transform_opportunities(self, records: list[dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
        return _transform(records, OPPORTUNITY_COLUMNS, "opportunities")
