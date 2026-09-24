"""Dashboard summary router — aggregate stats for the main dashboard."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns aggregate stats for the current user's dashboard:
    - Connected repo count
    - Total findings by severity
    - Recent scans (last 10)
    - Average security score
    """
    # Repos owned by user
    repo_result = await db.execute(
        select(Repository.id).where(
            Repository.user_id == current_user.id,
            Repository.is_active == True,  # noqa: E712
        )
    )
    repo_ids = [r for r in repo_result.scalars().all()]

    if not repo_ids:
        return {
            "repo_count": 0,
            "findings_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "recent_scans": [],
            "average_score": None,
        }

    # Recent scans
    scans_result = await db.execute(
        select(Scan)
        .where(Scan.repo_id.in_(repo_ids))
        .order_by(Scan.started_at.desc())
        .limit(10)
    )
    recent_scans = scans_result.scalars().all()
    scan_ids = [s.id for s in recent_scans]

    # Findings counts (only for completed scans' findings)
    completed_scan_ids_result = await db.execute(
        select(Scan.id).where(
            Scan.repo_id.in_(repo_ids),
            Scan.status == "completed",
        )
    )
    completed_scan_ids = completed_scan_ids_result.scalars().all()

    sev_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    if completed_scan_ids:
        for sev in sev_counts:
            cnt_result = await db.execute(
                select(func.count()).where(
                    Finding.scan_id.in_(completed_scan_ids),
                    Finding.severity == sev,
                    Finding.status == "open",
                )
            )
            sev_counts[sev] = cnt_result.scalar_one()

    # Average security score across completed scans
    avg_result = await db.execute(
        select(func.avg(Scan.security_score)).where(
            Scan.repo_id.in_(repo_ids),
            Scan.status == "completed",
            Scan.security_score.is_not(None),
        )
    )
    avg_score = avg_result.scalar_one_or_none()

    return {
        "repo_count": len(repo_ids),
        "findings_by_severity": sev_counts,
        "recent_scans": [
            {
                "id": s.id,
                "repo_id": s.repo_id,
                "status": s.status,
                "security_score": s.security_score,
                "total_findings": s.total_findings,
                "started_at": s.started_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in recent_scans
        ],
        "average_score": round(float(avg_score), 1) if avg_score is not None else None,
    }
