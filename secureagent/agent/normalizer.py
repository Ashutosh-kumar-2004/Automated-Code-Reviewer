"""
Finding normalizer: converts raw scanner output to standardized FindingSchema
and computes deterministic SHA256 fingerprints for deduplication.
"""
import hashlib
import re
from typing import Any
from agent.schemas import FindingSchema, RawFinding, SeverityType


def normalize_whitespace(text: str) -> str:
    """Strip extraneous whitespace for stable hashing across line end variations."""
    return " ".join(text.split())


def compute_fingerprint(rule_id: str, file_path: str, code_snippet: str) -> str:
    """
    Computes deterministic SHA256 fingerprint:
    sha256("{rule_id}:{file_path}:{normalized_whitespace_code}")
    """
    cleaned_code = normalize_whitespace(code_snippet)
    payload = f"{rule_id}:{file_path}:{cleaned_code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def map_severity(raw_severity: str) -> SeverityType:
    """Normalize scanner severity strings to critical, high, medium, low, info."""
    raw = str(raw_severity).lower().strip()
    if raw in ("error", "critical", "crit"):
        return "critical"
    if raw in ("high", "warn", "warning"):
        return "high"
    if raw in ("medium", "med"):
        return "medium"
    if raw in ("low",):
        return "low"
    return "info"


def extract_cwe_and_owasp(metadata: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Extract standard CWE IDs and OWASP categories from scanner metadata."""
    cwe_ids: list[str] = []
    owasp_tags: list[str] = []

    # Check for direct keys
    raw_cwe = metadata.get("cwe") or metadata.get("cwe_id") or metadata.get("cwe-id")
    if isinstance(raw_cwe, list):
        for item in raw_cwe:
            matches = re.findall(r"CWE-\d+", str(item), re.IGNORECASE)
            cwe_ids.extend([m.upper() for m in matches])
    elif isinstance(raw_cwe, str):
        matches = re.findall(r"CWE-\d+", raw_cwe, re.IGNORECASE)
        cwe_ids.extend([m.upper() for m in matches])

    raw_owasp = metadata.get("owasp") or metadata.get("owasp-top-10") or metadata.get("owasp_top_10")
    if isinstance(raw_owasp, list):
        for item in raw_owasp:
            matches = re.findall(r"A\d{2}:\d{4}", str(item), re.IGNORECASE)
            owasp_tags.extend([m.upper() for m in matches])
    elif isinstance(raw_owasp, str):
        matches = re.findall(r"A\d{2}:\d{4}", raw_owasp, re.IGNORECASE)
        owasp_tags.extend([m.upper() for m in matches])

    # Deduplicate while preserving order
    return list(dict.fromkeys(cwe_ids)), list(dict.fromkeys(owasp_tags))


def normalize_raw_finding(raw: RawFinding) -> FindingSchema:
    """Normalize a raw scanner result into a FindingSchema."""
    cwe_ids, owasp_tags = extract_cwe_and_owasp(raw.metadata)
    fingerprint = compute_fingerprint(raw.rule_id, raw.file_path, raw.code)
    severity = map_severity(raw.severity_raw)

    title = raw.metadata.get("shortlink") or raw.rule_id.split(".")[-1].replace("-", " ").capitalize()
    if not title or len(title) < 4:
        title = raw.rule_id

    return FindingSchema(
        rule_id=raw.rule_id,
        fingerprint=fingerprint,
        title=title,
        description=raw.message,
        severity=severity,
        confidence=float(raw.metadata.get("confidence", 0.8)),
        file_path=raw.file_path,
        line_start=raw.start_line,
        line_end=raw.end_line,
        code_snippet=raw.code,
        cwe_ids=cwe_ids,
        owasp_tags=owasp_tags,
        scanner=raw.scanner,
        status="open",
    )
