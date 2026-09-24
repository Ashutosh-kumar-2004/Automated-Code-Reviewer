"""Pydantic schemas for Scan endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field


class ScanPublic(BaseModel):
    id: str
    repo_id: str
    status: str
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    security_score: float | None
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    commit_sha: str | None
    tokens_used: int

    model_config = {"from_attributes": True}


class CreateScanRequest(BaseModel):
    repo_id: str = Field(..., description="Internal repository ID")
    # Future: options like severity_override, scanner_set, etc.


class ScanStatusResponse(BaseModel):
    scan: ScanPublic
    # Latest agent log message (for quick status polling without full SSE)
    latest_log: str | None = None
