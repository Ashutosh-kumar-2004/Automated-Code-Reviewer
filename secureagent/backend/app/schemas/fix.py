"""Pydantic schemas for Fix endpoints."""
from datetime import datetime

from pydantic import BaseModel


class FixPublic(BaseModel):
    id: str
    finding_id: str
    patch_diff: str | None
    explanation: str | None
    attempt_number: int
    status: str
    verified: bool
    verify_output: str | None
    model_used: str | None
    files_changed: str | None   # JSON array
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveFixRequest(BaseModel):
    """Optional body for approve — could extend with comment."""
    pass


class RejectFixRequest(BaseModel):
    reason: str | None = None
