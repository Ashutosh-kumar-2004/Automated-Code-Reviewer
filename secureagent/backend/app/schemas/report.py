"""Security Report Pydantic schemas."""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class FindingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    title: str
    description: str
    severity: str
    confidence: float
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    cwe_ids: list[str] = []
    owasp_tags: list[str] = []
    status: str


class ComplianceItem(BaseModel):
    category: str
    count: int
    severity: str
    findings: list[str] = []


class SecurityReportDetail(BaseModel):
    scan_id: str
    repo_id: str
    repo_name: str
    repo_url: str
    default_branch: str
    scanned_at: datetime | None
    security_score: float
    grade: str  # A+, A, B, C, F
    risk_level: str  # Minimal, Moderate, High, Critical
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    owasp_breakdown: list[ComplianceItem]
    cwe_breakdown: list[ComplianceItem]
    findings: list[FindingSummary]
    summary_markdown: str


class ReportListItem(BaseModel):
    scan_id: str
    repo_id: str
    repo_name: str
    security_score: float | None
    grade: str
    risk_level: str
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    created_at: datetime
    completed_at: datetime | None
