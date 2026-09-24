"""Fixes router — list fix attempts, approve/reject."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_owned_finding
from app.models.fix import Fix
from app.models.user import User
from app.schemas.fix import ApproveFixRequest, FixPublic, RejectFixRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fixes"])


async def _get_owned_fix(fix_id: str, current_user: User, db: AsyncSession) -> Fix:
    result = await db.execute(select(Fix).where(Fix.id == fix_id))
    fix = result.scalar_one_or_none()
    if fix is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fix not found")
    # IDOR: verify through finding chain
    await get_owned_finding(fix.finding_id, current_user, db)
    return fix


@router.get("/findings/{finding_id}/fixes", response_model=list[FixPublic])
async def list_fixes_for_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FixPublic]:
    await get_owned_finding(finding_id, current_user, db)
    result = await db.execute(
        select(Fix)
        .where(Fix.finding_id == finding_id)
        .order_by(Fix.attempt_number)
    )
    fixes = result.scalars().all()
    return [FixPublic.model_validate(f) for f in fixes]


@router.post("/fixes/{fix_id}/approve", response_model=FixPublic)
async def approve_fix(
    fix_id: str,
    body: ApproveFixRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FixPublic:
    fix = await _get_owned_fix(fix_id, current_user, db)
    if fix.status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only verified fixes can be approved",
        )
    fix.status = "approved"
    fix.approved_by = current_user.id
    fix.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(fix)
    logger.info("Fix %s approved by user %s", fix_id, current_user.login)
    return FixPublic.model_validate(fix)


@router.post("/fixes/{fix_id}/reject", response_model=FixPublic)
async def reject_fix(
    fix_id: str,
    body: RejectFixRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FixPublic:
    fix = await _get_owned_fix(fix_id, current_user, db)
    fix.status = "rejected"
    if body.reason:
        fix.verify_output = f"Rejected by user: {body.reason}"
    await db.commit()
    await db.refresh(fix)
    logger.info("Fix %s rejected by user %s", fix_id, current_user.login)
    return FixPublic.model_validate(fix)
