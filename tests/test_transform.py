"""Unit tests for etl.transform — no external services needed."""

import pandas as pd
import pytest

from etl.transform import TransformEngine


@pytest.fixture
def engine():
    return TransformEngine()


# ── Sample Salesforce-like records ───────────────────────────────

SAMPLE_ACCOUNTS = [
    {"Id": "001A", "Name": "Acme Health", "Industry": "Healthcare", "Type": "Customer",
     "Website": "https://acme.example.com", "Phone": "555-0100",
     "BillingCity": "Arlington", "BillingState": "VA",
     "AnnualRevenue": 5000000, "CreatedDate": "2024-01-15T10:00:00.000+0000"},
    {"Id": "001B", "Name": "Beta Hospital", "Industry": None, "Type": "Prospect",
     "Website": None, "Phone": None,
     "BillingCity": None, "BillingState": "CA",
     "AnnualRevenue": None, "CreatedDate": "2024-03-20T14:30:00.000+0000"},
    # Duplicate sf_id — should be deduped (keep last)
    {"Id": "001A", "Name": "Acme Health (Updated)", "Industry": "Healthcare", "Type": "Customer",
     "Website": "https://acme.example.com", "Phone": "555-0101",
     "BillingCity": "Arlington", "BillingState": "VA",
     "AnnualRevenue": 6000000, "CreatedDate": "2024-01-15T10:00:00.000+0000"},
]

SAMPLE_CONTACTS = [
    {"Id": "003A", "AccountId": "001A", "FirstName": "Jane", "LastName": "Doe",
     "Email": "jane@acme.example.com", "Phone": "555-0200",
     "Title": "CIO", "Department": "IT", "CreatedDate": "2024-02-01T09:00:00.000+0000"},
    {"Id": "003B", "AccountId": "001B", "FirstName": None, "LastName": "Smith",
     "Email": None, "Phone": None,
     "Title": None, "Department": None, "CreatedDate": None},
]

SAMPLE_OPPORTUNITIES = [
    {"Id": "006A", "AccountId": "001A", "Name": "Big Deal",
     "StageName": "Negotiation", "Amount": 75000, "CloseDate": "2024-06-30",
     "Probability": 60, "CreatedDate": "2024-01-20T08:00:00.000+0000"},
    {"Id": "006B", "AccountId": "001B", "Name": "Small Deal",
     "StageName": "Prospecting", "Amount": 5000, "CloseDate": "2024-12-31",
     "Probability": 20, "CreatedDate": "2024-04-10T12:00:00.000+0000"},
]


# ── Tests ────────────────────────────────────────────────────────

class TestTransformAccounts:
    def test_deduplication(self, engine):
        df, stats = engine.transform_accounts(SAMPLE_ACCOUNTS)
        assert stats["dedup_count"] == 1
        assert stats["output_count"] == 2
        # The kept record should be the last duplicate (updated name)
        acme = df[df["sf_id"] == "001A"].iloc[0]
        assert acme["name"] == "Acme Health (Updated)"

    def test_column_renaming(self, engine):
        df, _ = engine.transform_accounts(SAMPLE_ACCOUNTS)
        assert "sf_id" in df.columns
        assert "Id" not in df.columns
        assert "billing_city" in df.columns
        assert "BillingCity" not in df.columns

    def test_null_handling(self, engine):
        df, stats = engine.transform_accounts(SAMPLE_ACCOUNTS)
        null_counts = stats["null_counts"]
        assert null_counts["industry"] >= 1  # Beta Hospital has null industry
        assert null_counts["website"] >= 1

    def test_date_parsing(self, engine):
        df, _ = engine.transform_accounts(SAMPLE_ACCOUNTS)
        assert pd.api.types.is_datetime64_any_dtype(df["created_date"])

    def test_synced_at_added(self, engine):
        df, _ = engine.transform_accounts(SAMPLE_ACCOUNTS)
        assert "synced_at" in df.columns
        assert df["synced_at"].notna().all()

    def test_empty_input(self, engine):
        df, stats = engine.transform_accounts([])
        assert len(df) == 0
        assert stats["input_count"] == 0


class TestTransformContacts:
    def test_output_shape(self, engine):
        df, stats = engine.transform_contacts(SAMPLE_CONTACTS)
        assert stats["output_count"] == 2
        assert "account_id" in df.columns

    def test_null_fields_preserved(self, engine):
        df, _ = engine.transform_contacts(SAMPLE_CONTACTS)
        smith = df[df["sf_id"] == "003B"].iloc[0]
        assert pd.isna(smith["first_name"])
        assert pd.isna(smith["email"])


class TestTransformOpportunities:
    def test_output_shape(self, engine):
        df, stats = engine.transform_opportunities(SAMPLE_OPPORTUNITIES)
        assert stats["output_count"] == 2
        assert "stage_name" in df.columns
        assert "amount" in df.columns

    def test_no_duplicates(self, engine):
        _, stats = engine.transform_opportunities(SAMPLE_OPPORTUNITIES)
        assert stats["dedup_count"] == 0
