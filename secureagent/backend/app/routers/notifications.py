"""
Remediation Notifications router — detects unresolved vulnerabilities across repositories
and informs the frontend remediator agent / notification modal.
Configurable notification cadence via REMEDIATION_NOTIFICATION_INTERVAL_MINUTES.
"""
import logging
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/notifications", tags=["notifications"])


class AffectedRepoSummary(BaseModel):
    repo_id: str
    repo_name: str
    count: int


class UrgentFindingSummary(BaseModel):
    id: str
    title: str
    severity: str
    rule_id: str
    file_path: str
    line_start: int | None


class RemediationNotificationResponse(BaseModel):
    has_vulnerabilities: bool
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    interval_minutes: int
    interval_seconds: int
    affected_repos: list[AffectedRepoSummary]
    urgent_findings: list[UrgentFindingSummary]
    alert_title: str
    alert_message: str


@router.get("/remediation", response_model=RemediationNotificationResponse)
async def get_remediation_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemediationNotificationResponse:
    """
    Checks if active/open vulnerabilities are present across the user's repositories.
    Returns remediation notification payload along with the configured interval.
    """
    curr_settings = get_settings()
    interval_mins = curr_settings.remediation_notification_interval_minutes or 60
    interval_secs = interval_mins * 60

    # 1. Fetch user's active repositories
    repos_query = select(Repository).where(
        Repository.user_id == current_user.id,
        Repository.is_active == True,
    )
    repos_res = await db.execute(repos_query)
    repos = repos_res.scalars().all()

    if not repos:
        return RemediationNotificationResponse(
            has_vulnerabilities=False,
            total_vulnerabilities=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            interval_minutes=interval_mins,
            interval_seconds=interval_secs,
            affected_repos=[],
            urgent_findings=[],
            alert_title="System Secure",
            alert_message="No connected repositories found.",
        )

    # 2. For each repository, find the latest completed scan and query open findings
    all_open_findings: list[tuple[Finding, str]] = []  # (finding, repo_name)
    repo_finding_counts: dict[str, tuple[str, int]] = {}  # repo_id -> (repo_name, count)

    for r in repos:
        # Get latest completed scan for this repo
        scan_query = (
            select(Scan)
            .where(Scan.repo_id == r.id, Scan.status == "completed")
            .order_by(Scan.completed_at.desc())
            .limit(1)
        )
        scan_res = await db.execute(scan_query)
        latest_scan = scan_res.scalar_one_or_none()

        if latest_scan:
            findings_query = select(Finding).where(
                Finding.scan_id == latest_scan.id,
                Finding.status == "open",
            )
            findings_res = await db.execute(findings_query)
            open_findings = findings_res.scalars().all()

            if open_findings:
                repo_finding_counts[r.id] = (r.full_name, len(open_findings))
                for f in open_findings:
                    all_open_findings.append((f, r.full_name))

    total = len(all_open_findings)
    if total == 0:
        return RemediationNotificationResponse(
            has_vulnerabilities=False,
            total_vulnerabilities=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            interval_minutes=interval_mins,
            interval_seconds=interval_secs,
            affected_repos=[],
            urgent_findings=[],
            alert_title="All Systems Clean",
            alert_message="Zero unresolved vulnerabilities detected across all connected repositories.",
        )

    critical_c = sum(1 for f, _ in all_open_findings if f.severity == "critical")
    high_c = sum(1 for f, _ in all_open_findings if f.severity == "high")
    medium_c = sum(1 for f, _ in all_open_findings if f.severity == "medium")
    low_c = sum(1 for f, _ in all_open_findings if f.severity == "low")

    # Order urgent findings (critical first, then high)
    def severity_rank(sev: str) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(sev.lower(), 4)

    sorted_findings = sorted(all_open_findings, key=lambda x: severity_rank(x[0].severity))
    top_urgent = [
        UrgentFindingSummary(
            id=f.id,
            title=f.title,
            severity=f.severity,
            rule_id=f.rule_id,
            file_path=f.file_path,
            line_start=f.line_start,
        )
        for f, _ in sorted_findings[:5]
    ]

    affected_list = [
        AffectedRepoSummary(repo_id=rid, repo_name=name, count=cnt)
        for rid, (name, cnt) in repo_finding_counts.items()
    ]

    if critical_c > 0:
        alert_title = f"🚨 Remediation Alert: {critical_c} Critical Vulnerabilities Require Attention"
        alert_msg = (
            f"SecureAgent detected {total} unresolved vulnerabilities ({critical_c} critical) across "
            f"{len(affected_list)} connected repositories. Autonomous remediation is recommended immediately."
        )
    elif high_c > 0:
        alert_title = f"⚠️ Remediation Alert: {high_c} High Severity Vulnerabilities Detected"
        alert_msg = (
            f"SecureAgent detected {total} security issues requiring attention. "
            "Deploy AI-assisted fixes to maintain repository security score."
        )
    else:
        alert_title = f"🛡️ Remediation Notice: {total} Findings Pending Review"
        alert_msg = f"There are {total} open security findings across your repositories."

    return RemediationNotificationResponse(
        has_vulnerabilities=True,
        total_vulnerabilities=total,
        critical_count=critical_c,
        high_count=high_c,
        medium_count=medium_c,
        low_count=low_c,
        interval_minutes=interval_mins,
        interval_seconds=interval_secs,
        affected_repos=affected_list,
        urgent_findings=top_urgent,
        alert_title=alert_title,
        alert_message=alert_msg,
    )
