"""
Stub scan task dispatcher.
Phase 1: no-op placeholder — the actual agent logic is built in Phase 2+.
The function signature is designed to become a Celery task in Phase 6
with a single @celery_app.task decorator (no rewrite needed).
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.scan_runner import execute_scan_pipeline

logger = logging.getLogger(__name__)


_running_tasks: set[asyncio.Task] = set()


async def dispatch_scan(scan_id: str, user_id: str, db: AsyncSession) -> None:
    """
    Dispatch a scan job asynchronously.
    Executes the Ingest and Semgrep scan pipeline in the background.
    Maintains a strong reference to prevent GC cancellation.
    """
    logger.info("Dispatching scan %s for user %s", scan_id, user_id)
    task = asyncio.create_task(execute_scan_pipeline(scan_id, user_id))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
