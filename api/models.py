from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class AccountResponse(BaseModel):
    sf_id: str
    name: str
    industry: Optional[str] = None
    type: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    annual_revenue: Optional[float] = None
    created_date: Optional[datetime] = None
    synced_at: Optional[datetime] = None


class ContactResponse(BaseModel):
    sf_id: str
    account_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    created_date: Optional[datetime] = None
    synced_at: Optional[datetime] = None


class OpportunityResponse(BaseModel):
    sf_id: str
    account_id: Optional[str] = None
    name: str
    stage_name: Optional[str] = None
    amount: Optional[float] = None
    close_date: Optional[datetime] = None
    probability: Optional[float] = None
    created_date: Optional[datetime] = None
    synced_at: Optional[datetime] = None


class PipelineSummary(BaseModel):
    stage_name: Optional[str] = None
    deal_count: int
    total_amount: Optional[float] = None
    avg_amount: Optional[float] = None
    avg_probability: Optional[float] = None


class SyncTriggerResponse(BaseModel):
    run_id: str
    status: str


class SyncStatusResponse(BaseModel):
    run_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    records_extracted: Optional[int] = None
    records_loaded: Optional[int] = None
    error_message: Optional[str] = None
