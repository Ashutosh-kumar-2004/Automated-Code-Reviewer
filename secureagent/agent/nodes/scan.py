"""
ScanNode — Executes Semgrep security scanner and normalizes all detected vulnerabilities.
"""
import logging
from agent.normalizer import normalize_raw_finding
from agent.scanners.semgrep_scanner import SemgrepScanner
from agent.schemas import FindingSchema
from agent.state import AgentState

logger = logging.getLogger(__name__)


def calculate_security_score(findings: list[FindingSchema]) -> float:
    """
    Computes security score based on formula:
    score = max(0, 100 - (critical * 10) - (high * 5) - (medium * 2) - (low * 0.5))
    """
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")
    medium = sum(1 for f in findings if f.severity == "medium")
    low = sum(1 for f in findings if f.severity == "low")

    deductions = (critical * 10.0) + (high * 5.0) + (medium * 2.0) + (low * 0.5)
    return round(max(0.0, 100.0 - deductions), 1)


class ScanNode:
    def __init__(self, scanner: SemgrepScanner | None = None):
        self.scanner = scanner or SemgrepScanner()

    async def run(self, state: AgentState) -> AgentState:
        workspace_dir = state.get("workspace_dir")
        if not workspace_dir:
            state["error"] = "Workspace directory not found in state"
            state["status"] = "failed"
            return state

        logger.info("Scanning workspace: %s", workspace_dir)
        raw_findings = await self.scanner.scan(workspace_dir)

        normalized_findings: list[FindingSchema] = []
        seen_fingerprints: set[str] = set()

        for raw in raw_findings:
            f = normalize_raw_finding(raw)
            if f.fingerprint not in seen_fingerprints:
                seen_fingerprints.add(f.fingerprint)
                normalized_findings.append(f)

        state["findings"] = normalized_findings
        state["security_score"] = calculate_security_score(normalized_findings)
        state["status"] = "scanned"
        logger.info(
            "Scan completed: %d findings, security score: %.1f",
            len(normalized_findings),
            state["security_score"],
        )
        return state
