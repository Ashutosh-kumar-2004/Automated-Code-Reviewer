"""
Agent state representation across the scan lifecycle.
"""
from typing import Any, TypedDict
from agent.schemas import FindingSchema, PatchSchema


class AgentState(TypedDict, total=False):
    scan_id: str
    user_id: str
    repo_id: str
    repo_url: str
    repo_name: str
    default_branch: str
    workspace_dir: str
    detected_language: str
    test_runner: str | None
    findings: list[FindingSchema]
    current_finding_idx: int
    fixes: list[PatchSchema]
    security_score: float
    error: str | None
    status: str
