"""
Scans router — trigger, status, cancel, SSE stream.
SSE endpoint tails agent_logs table and supports Last-Event-ID replay.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.middleware.auth import get_current_user, get_owned_repo, get_owned_scan
from app.models.agent_log import AgentLog
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User
from app.schemas.scan import CreateScanRequest, ScanPublic, ScanStatusResponse
from app.tasks.scan_task import dispatch_scan

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/scans", tags=["scans"])

ACTIVE_SCAN_STATUSES = ["pending", "cloning", "scanning", "triaging", "fixing", "verifying"]


async def _count_active_scans(db: AsyncSession, user_id: str | None = None) -> int:
    query = select(func.count()).select_from(Scan).where(Scan.status.in_(ACTIVE_SCAN_STATUSES))
    if user_id:
        query = query.join(Repository, Scan.repo_id == Repository.id).where(Repository.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one()


@router.post("", response_model=ScanPublic, status_code=status.HTTP_201_CREATED)
async def create_scan(
    body: CreateScanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanPublic:
    """
    Trigger a new scan on a connected repository.
    Enforces:
      - IDOR: repo must belong to current_user
      - Auto-recovers stale scans older than 10 minutes
      - One active scan per repo
      - MAX_CONCURRENT_SCANS per user cap
    """
    repo = await get_owned_repo(body.repo_id, current_user, db)

    # Auto-recover any stale scans older than 10 minutes so they don't block queues
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    stale_scans = await db.execute(
        select(Scan).where(
            Scan.status.in_(ACTIVE_SCAN_STATUSES),
            Scan.started_at < stale_cutoff,
        )
    )
    for s in stale_scans.scalars().all():
        s.status = "failed"
        s.error_message = "Scan timed out / aborted"
    await db.commit()

    # One active scan per repo
    active_for_repo = await db.execute(
        select(Scan).where(
            Scan.repo_id == repo.id,
            Scan.status.in_(ACTIVE_SCAN_STATUSES),
        )
    )
    if active_for_repo.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scan is already running for this repository. Please wait for it to complete.",
        )

    # Concurrency cap per user
    active_user_total = await _count_active_scans(db, user_id=current_user.id)
    if active_user_total >= settings.max_concurrent_scans:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum concurrent scans ({settings.max_concurrent_scans}) reached for your account. Please wait for current scans to finish.",
        )

    scan = Scan(repo_id=repo.id, status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # Dispatch to background task (BackgroundTasks MVP → Celery in Phase 6)
    await dispatch_scan(scan.id, current_user.id, db)

    logger.info("Scan %s created for repo %s", scan.id, repo.full_name)
    return ScanPublic.model_validate(scan)


@router.get("/{scan_id}", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScanStatusResponse:
    scan = await get_owned_scan(scan_id, current_user, db)

    # Latest log message for quick polling
    latest_log_result = await db.execute(
        select(AgentLog.message)
        .where(AgentLog.scan_id == scan_id)
        .order_by(AgentLog.event_id.desc())
        .limit(1)
    )
    latest_log = latest_log_result.scalar_one_or_none()

    return ScanStatusResponse(
        scan=ScanPublic.model_validate(scan),
        latest_log=latest_log,
    )


@router.post("/{scan_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    scan = await get_owned_scan(scan_id, current_user, db)
    if scan.is_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan is already in terminal state: {scan.status}",
        )
    scan.status = "cancelled"
    scan.completed_at = datetime.now(timezone.utc)
    scan.error_message = "Cancelled by user"
    await db.commit()
    logger.info("Scan %s cancelled by user %s", scan_id, current_user.login)
    return {"message": "Scan cancelled", "scan_id": scan_id}


@router.get("/{scan_id}/stream")
async def stream_scan_events(
    scan_id: str,
    request: Request,
    last_event_id: str | None = Header(None, alias="last-event-id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Server-Sent Events endpoint.
    Tails agent_logs for the given scan starting from last_event_id.
    Supports Last-Event-ID replay for reconnection.
    """
    # Ownership check
    await get_owned_scan(scan_id, current_user, db)

    last_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

    async def event_generator():
        nonlocal last_id
        try:
            while True:
                if await request.is_disconnected():
                    break

                async with db.begin_nested():
                    result = await db.execute(
                        select(AgentLog)
                        .where(
                            AgentLog.scan_id == scan_id,
                            AgentLog.event_id > last_id,
                        )
                        .order_by(AgentLog.event_id)
                        .limit(50)
                    )
                    logs = result.scalars().all()

                for log in logs:
                    data = {
                        "node": log.node_name,
                        "level": log.level,
                        "message": log.message,
                        "timestamp": log.timestamp.isoformat(),
                        "metadata": json.loads(log.metadata_json) if log.metadata_json else {},
                    }
                    yield f"id: {log.event_id}\ndata: {json.dumps(data)}\n\n"
                    last_id = log.event_id

                # Check if scan has reached a terminal state
                scan_result = await db.execute(
                    select(Scan.status).where(Scan.id == scan_id)
                )
                scan_status = scan_result.scalar_one_or_none()
                if scan_status in ("completed", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps({'status': scan_status})}\n\n"
                    break

                await asyncio.sleep(0.75)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
