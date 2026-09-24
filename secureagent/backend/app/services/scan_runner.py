"""
ScanRunner service — orchestrates IngestNode and ScanNode for a scan,
records AgentLog entries for SSE streaming, persists findings to the database,
and updates repository metrics.
"""
import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
# Ensure agent package is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
secureagent_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if secureagent_root not in sys.path:
    sys.path.insert(0, secureagent_root)

from agent.nodes.ingest import IngestNode
from agent.nodes.scan import ScanNode
from agent.state import AgentState
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.agent_log import AgentLog
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User
from app.services.crypto import decrypt_token

logger = logging.getLogger(__name__)
settings = get_settings()


async def add_agent_log(
    db: AsyncSession,
    scan_id: str,
    node_name: str,
    message: str,
    level: str = "info",
    metadata: dict | None = None,
) -> None:
    """Append a real-time event log for SSE streaming."""
    res = await db.execute(
        select(func.coalesce(func.max(AgentLog.event_id), 0)).where(
            AgentLog.scan_id == scan_id
        )
    )
    next_event_id = res.scalar_one() + 1

    log = AgentLog(
        scan_id=scan_id,
        event_id=next_event_id,
        node_name=node_name,
        level=level,
        message=message,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(log)
    await db.commit()


async def execute_scan_pipeline(scan_id: str, user_id: str) -> None:
    """Async background task that runs the scan pipeline to completion."""
    async with AsyncSessionLocal() as db:
        scan = await db.get(Scan, scan_id)
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return

        repo = await db.get(Repository, scan.repo_id)
        user = await db.get(User, user_id)
        if not repo or not user:
            logger.error("Repo or user not found for scan %s", scan_id)
            scan.status = "failed"
            scan.error_message = "Associated repository or user not found"
            await db.commit()
            return

        gh_token = decrypt_token(user.access_token_encrypted or "")
        scan.status = "cloning"
        scan.started_at = datetime.now(timezone.utc)
        await db.commit()

        await add_agent_log(
            db, scan_id, "ingest",
            f"Cloning repository {repo.full_name} ({repo.default_branch})...",
            level="info",
        )

        state: AgentState = {
            "scan_id": scan_id,
            "user_id": user_id,
            "repo_id": repo.id,
            "repo_url": repo.clone_url,
            "repo_name": repo.full_name,
            "default_branch": repo.default_branch,
            "findings": [],
            "fixes": [],
        }

        workspace_dir = None
        try:
            # 1. INGEST NODE
            ingest_node = IngestNode(workspace_root=settings.workspace_root)
            state = await ingest_node.run(state, token=gh_token)

            if state.get("error"):
                raise RuntimeError(state["error"])

            workspace_dir = state.get("workspace_dir")
            await add_agent_log(
                db, scan_id, "ingest",
                f"Repository cloned. Detected language: {state.get('detected_language')}. Test runner: {state.get('test_runner') or 'none'}",
                level="info",
            )

            # 2. SCAN NODE
            scan.status = "scanning"
            await db.commit()

            await add_agent_log(
                db, scan_id, "scan",
                "Executing Semgrep vulnerability scanner and rule engines...",
                level="info",
            )

            scan_node = ScanNode()
            state = await scan_node.run(state)

            if state.get("error"):
                raise RuntimeError(state["error"])

            findings = state.get("findings", [])
            security_score = state.get("security_score", 100.0)

            # 3. PERSIST FINDINGS TO DB
            for f in findings:
                finding_row = Finding(
                    scan_id=scan_id,
                    rule_id=f.rule_id,
                    fingerprint=f.fingerprint,
                    title=f.title,
                    description=f.description,
                    severity=f.severity,
                    confidence=f.confidence,
                    file_path=f.file_path,
                    line_start=f.line_start,
                    line_end=f.line_end,
                    code_snippet=f.code_snippet,
                    cwe_ids=json.dumps(f.cwe_ids),
                    owasp_tags=json.dumps(f.owasp_tags),
                    scanner=f.scanner,
                    status="open",
                )
                db.add(finding_row)

            # 4. MARK SCAN COMPLETED
            scan.status = "completed"
            scan.security_score = security_score
            scan.total_findings = len(findings)
            scan.critical_count = sum(1 for f in findings if f.severity == "critical")
            scan.high_count = sum(1 for f in findings if f.severity == "high")
            scan.medium_count = sum(1 for f in findings if f.severity == "medium")
            scan.low_count = sum(1 for f in findings if f.severity == "low")
            scan.completed_at = datetime.now(timezone.utc)
            repo.last_scanned_at = scan.completed_at
            await db.commit()

            await add_agent_log(
                db, scan_id, "completed",
                f"Scan finished! Discovered {len(findings)} findings. Overall Security Score: {security_score}/100",
                level="info",
                metadata={"findings_count": len(findings), "score": security_score},
            )
            logger.info("Scan %s completed successfully with %d findings", scan_id, len(findings))

        except Exception as exc:
            logger.exception("Scan %s failed: %s", scan_id, exc)
            scan.status = "failed"
            scan.error_message = str(exc) if str(exc).strip() else f"{type(exc).__name__}"
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await add_agent_log(
                db, scan_id, "error",
                f"Scan failed: {scan.error_message}",
                level="error",
            )
        finally:
            if workspace_dir and os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir, ignore_errors=True)
