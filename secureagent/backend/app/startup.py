"""
Startup recovery: on every FastAPI boot, mark stale running scans as failed.
This handles the case where the process was killed mid-scan.
"""
import logging

from sqlalchemy import update

from app.database import AsyncSessionLocal
from app.models.scan import SCAN_STATUS_VALUES

logger = logging.getLogger(__name__)

STALE_STATUSES = [
    s for s in SCAN_STATUS_VALUES if s not in ("completed", "failed", "cancelled", "pending")
]


async def mark_stale_scans_failed() -> None:
    """Called at application startup via lifespan context manager."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(  # type: ignore[arg-type]
                __import__("app.models.scan", fromlist=["Scan"]).Scan  # noqa: F821
            )
            .where(
                __import__("app.models.scan", fromlist=["Scan"]).Scan.status.in_(STALE_STATUSES)
            )
            .values(
                status="failed",
                error_message="Process restarted — scan was interrupted",
            )
            .returning(
                __import__("app.models.scan", fromlist=["Scan"]).Scan.id
            )
        )
        stale_ids = result.scalars().all()
        await db.commit()
        if stale_ids:
            logger.warning(
                "Marked %d stale scan(s) as failed on startup: %s",
                len(stale_ids),
                stale_ids,
            )
        else:
            logger.info("No stale scans found on startup")
