"""Pydantic schemas for Finding endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field


class FindingPublic(BaseModel):
    id: str
    scan_id: str
    rule_id: str
    scanner: str
    title: str
    description: str | None
    fingerprint: str
    severity: str
    confidence: float
    file_path: str
    line_start: int | None
    line_end: int | None
    # code_snippet is masked if is_masked=True
    code_snippet: str | None
    explanation: str | None
    cwe_ids: str | None       # JSON array string
    owasp_tags: str | None    # JSON array string
    status: str
    false_positive: bool
    is_masked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateFindingRequest(BaseModel):
    status: str | None = Field(
        None,
        description="One of: open, fixed, needs_review, false_positive, dismissed",
    )
    false_positive: bool | None = None


class FindingSuggestionResponse(BaseModel):
    finding_id: str
    explanation: str
    improved_code: str
    coding_style_improvements: list[str]
    best_practices: list[str]
    cwe_mitigation: str
    model: str = "gemini-3.6-flash"

