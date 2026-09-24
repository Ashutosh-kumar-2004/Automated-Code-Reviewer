"""
Security Reports router — lists audit reports, compliance breakdowns (OWASP/CWE),
and exports executive summaries in Markdown and JSON.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_owned_scan
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User
from app.schemas.report import (
    ComplianceItem,
    FindingSummary,
    ReportListItem,
    SecurityReportDetail,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _calculate_grade_and_risk(score: float | None, critical: int, high: int) -> tuple[str, str]:
    if score is None:
        return "N/A", "Unknown"
    if critical > 0:
        risk = "Critical Risk"
    elif high > 0:
        risk = "Elevated Risk"
    elif score < 80:
        risk = "Moderate Risk"
    else:
        risk = "Minimal Risk"

    if score >= 95:
        grade = "A+"
    elif score >= 85:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    else:
        grade = "F"
    return grade, risk


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportListItem]:
    """List completed security audit reports for all user repositories."""
    query = (
        select(Scan, Repository.full_name)
        .join(Repository, Scan.repo_id == Repository.id)
        .where(Repository.user_id == current_user.id, Scan.status == "completed")
        .order_by(Scan.completed_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    items: list[ReportListItem] = []
    for scan, repo_name in rows:
        grade, risk = _calculate_grade_and_risk(
            scan.security_score, scan.critical_count, scan.high_count
        )
        items.append(
            ReportListItem(
                scan_id=scan.id,
                repo_id=scan.repo_id,
                repo_name=repo_name,
                security_score=scan.security_score,
                grade=grade,
                risk_level=risk,
                total_findings=scan.total_findings,
                critical_count=scan.critical_count,
                high_count=scan.high_count,
                medium_count=scan.medium_count,
                low_count=scan.low_count,
                created_at=scan.created_at,
                completed_at=scan.completed_at,
            )
        )
    return items


@router.get("/{scan_id}", response_model=SecurityReportDetail)
async def get_report_detail(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SecurityReportDetail:
    """Retrieve full audit report with OWASP/CWE compliance mappings and remediation notes."""
    scan = await get_owned_scan(scan_id, current_user, db)
    repo = await db.get(Repository, scan.repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.scan_id == scan_id).order_by(Finding.severity)
    )
    findings = findings_res.scalars().all()

    grade, risk = _calculate_grade_and_risk(
        scan.security_score, scan.critical_count, scan.high_count
    )

    # Compute OWASP & CWE breakdowns
    owasp_counts: dict[str, list[str]] = {}
    cwe_counts: dict[str, list[str]] = {}
    finding_summaries: list[FindingSummary] = []

    for f in findings:
        cwe_list = json.loads(f.cwe_ids or "[]")
        owasp_list = json.loads(f.owasp_tags or "[]")

        for cwe in cwe_list:
            cwe_counts.setdefault(cwe, []).append(f.title)
        for owasp in owasp_list:
            owasp_counts.setdefault(owasp, []).append(f.title)

        finding_summaries.append(
            FindingSummary(
                id=f.id,
                rule_id=f.rule_id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                confidence=f.confidence,
                file_path=f.file_path,
                line_start=f.line_start,
                line_end=f.line_end,
                code_snippet=f.code_snippet,
                cwe_ids=cwe_list,
                owasp_tags=owasp_list,
                status=f.status,
            )
        )

    owasp_items = [
        ComplianceItem(
            category=k,
            count=len(v),
            severity="critical" if any("injection" in s.lower() for s in v) else "high",
            findings=v,
        )
        for k, v in owasp_counts.items()
    ]

    cwe_items = [
        ComplianceItem(
            category=k,
            count=len(v),
            severity="critical" if k in ("CWE-89", "CWE-502") else "high",
            findings=v,
        )
        for k, v in cwe_counts.items()
    ]

    summary_md = _generate_markdown_report(scan, repo, finding_summaries, grade, risk)

    return SecurityReportDetail(
        scan_id=scan.id,
        repo_id=repo.id,
        repo_name=repo.full_name,
        repo_url=repo.html_url,
        default_branch=repo.default_branch,
        scanned_at=scan.completed_at,
        security_score=scan.security_score or 100.0,
        grade=grade,
        risk_level=risk,
        total_findings=scan.total_findings,
        critical_count=scan.critical_count,
        high_count=scan.high_count,
        medium_count=scan.medium_count,
        low_count=scan.low_count,
        owasp_breakdown=owasp_items,
        cwe_breakdown=cwe_items,
        findings=finding_summaries,
        summary_markdown=summary_md,
    )


@router.get("/{scan_id}/export")
async def export_report(
    scan_id: str,
    format: Literal["markdown", "json"] = Query(default="markdown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download executive security report as Markdown or JSON."""
    report_detail = await get_report_detail(scan_id, current_user, db)

    if format == "json":
        return Response(
            content=report_detail.model_dump_json(indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="security-report-{scan_id[:8]}.json"'
            },
        )

    return Response(
        content=report_detail.summary_markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="security-report-{scan_id[:8]}.md"'
        },
    )


def _generate_markdown_report(
    scan: Scan,
    repo: Repository,
    findings: list[FindingSummary],
    grade: str,
    risk: str,
) -> str:
    timestamp = scan.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC") if scan.completed_at else "N/A"
    
    table_rows = []
    for f in findings:
        cwe_str = ", ".join(f.cwe_ids) or "N/A"
        table_rows.append(
            f"| `{f.severity.upper()}` | {f.title} | `{f.file_path}:{f.line_start}` | `{cwe_str}` |"
        )
    table_text = (
        "| Severity | Vulnerability | Location | CWE |\n"
        "| :--- | :--- | :--- | :--- |\n"
        + ("\n".join(table_rows) if table_rows else "| Info | Clean codebase | None | None |")
    )

    return f"""# 🛡️ Executive Security Assessment Report

**Repository**: [{repo.full_name}]({repo.html_url})  
**Branch**: `{repo.default_branch}`  
**Scan ID**: `{scan.id}`  
**Date Evaluated**: `{timestamp}`  
**Auditor**: SecureAgent Autonomous Remediation Engine  

---

## 📊 Executive Posture Summary

| Metric | Evaluation |
| :--- | :--- |
| **Overall Security Score** | **{scan.security_score or 100.0} / 100** |
| **Security Grade** | **{grade}** |
| **Risk Classification** | **{risk}** |
| **Total Findings** | **{scan.total_findings}** |
| **Critical Issues** | **{scan.critical_count}** |
| **High Severity Issues** | **{scan.high_count}** |
| **Medium Severity Issues** | **{scan.medium_count}** |
| **Low Severity Issues** | **{scan.low_count}** |

---

## 🔍 Vulnerability Inventory

{table_text}

---

## 📋 Remediation Recommendations

1. **Immediate Patch Application**: Review and merge automated remediation pull requests generated by SecureAgent for all Critical and High vulnerabilities.
2. **Secret Rotation**: If any hardcoded secrets (CWE-798) were flagged, purge commit history with `git filter-repo` and revoke old credentials at provider portals.
3. **Continuous Enforcement**: Integrate SecureAgent GitHub Action to block regression vulnerabilities on every pull request.

---
*Generated by [SecureAgent](https://github.com/apps/secureagent)*
"""
