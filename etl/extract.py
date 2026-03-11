import logging
import time
from typing import Any

import httpx
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError

from config import get_settings

logger = logging.getLogger(__name__)

SOQL_ACCOUNTS = """
SELECT Id, Name, Industry, Type, Website, Phone,
       BillingCity, BillingState, AnnualRevenue, CreatedDate
FROM Account
"""

SOQL_CONTACTS = """
SELECT Id, AccountId, FirstName, LastName, Email, Phone,
       Title, Department, CreatedDate
FROM Contact
"""

SOQL_OPPORTUNITIES = """
SELECT Id, AccountId, Name, StageName, Amount,
       CloseDate, Probability, CreatedDate
FROM Opportunity
"""


def _oauth_login(settings) -> Salesforce:
    """Authenticate via REST OAuth 2.0 client credentials flow."""
    token_url = f"https://{settings.sf_domain}/services/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": settings.sf_client_id,
        "client_secret": settings.sf_client_secret,
    }
    resp = httpx.post(token_url, data=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return Salesforce(
        instance_url=data["instance_url"],
        session_id=data["access_token"],
    )


class SalesforceExtractor:
    """Extracts data from Salesforce using the REST API via simple-salesforce."""

    def __init__(self) -> None:
        settings = get_settings()
        logger.info("Authenticating with Salesforce via OAuth 2.0 (%s)…", settings.sf_domain)
        self.sf = _oauth_login(settings)
        logger.info("Salesforce authentication successful.")

    def _query_with_retry(
        self, soql: str, max_retries: int = 3, base_delay: float = 2.0
    ) -> list[dict[str, Any]]:
        for attempt in range(1, max_retries + 1):
            try:
                result = self.sf.query_all(soql)
                records = result.get("records", [])
                for rec in records:
                    rec.pop("attributes", None)
                return records
            except SalesforceError as exc:
                if attempt == max_retries:
                    logger.error("Salesforce query failed after %d attempts: %s", max_retries, exc)
                    raise
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Salesforce query attempt %d/%d failed (%s). Retrying in %.1fs…",
                    attempt, max_retries, exc, delay,
                )
                time.sleep(delay)
        return []

    def extract_accounts(self) -> list[dict[str, Any]]:
        logger.info("Extracting accounts…")
        records = self._query_with_retry(SOQL_ACCOUNTS)
        logger.info("Extracted %d accounts.", len(records))
        return records

    def extract_contacts(self) -> list[dict[str, Any]]:
        logger.info("Extracting contacts…")
        records = self._query_with_retry(SOQL_CONTACTS)
        logger.info("Extracted %d contacts.", len(records))
        return records

    def extract_opportunities(self) -> list[dict[str, Any]]:
        logger.info("Extracting opportunities…")
        records = self._query_with_retry(SOQL_OPPORTUNITIES)
        logger.info("Extracted %d opportunities.", len(records))
        return records