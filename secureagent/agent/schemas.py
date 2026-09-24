"""
Pydantic schemas and typed definitions for the security scanning agent.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


SeverityType = Literal["critical", "high", "medium", "low", "info"]
FindingStatusType = Literal["open", "fixed", "needs_review", "false_positive", "dismissed"]


class RawFinding(BaseModel):
    """Raw scanner output before normalization."""
    rule_id: str
    message: str
    file_path: str
    start_line: int
    end_line: int
    code: str
    severity_raw: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    scanner: str = "semgrep"


class FindingSchema(BaseModel):
    """Standardized normalized security finding."""
    rule_id: str
    fingerprint: str
    title: str
    description: str
    severity: SeverityType
    confidence: float = 0.8
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    cwe_ids: list[str] = Field(default_factory=list)
    owasp_tags: list[str] = Field(default_factory=list)
    scanner: str = "semgrep"
    status: FindingStatusType = "open"


class PatchSchema(BaseModel):
    """Structured patch proposed by AI."""
    file_path: str
    line_start: int
    line_end: int
    replacement_code: str
    explanation: str
    diff: str | None = None
