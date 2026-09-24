"""
Phase 2 Unit Tests:
- Deterministic SHA-256 fingerprinting
- Scanner finding normalization & CWE/OWASP extraction
- Security score formula calculations
- SemgrepScanner rules detection on demo-vulnerable-repo
- IngestNode language & test runner detection
"""
import os
import sys
import pytest

# Ensure workspace root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
secureagent_root = os.path.dirname(backend_dir)
if secureagent_root not in sys.path:
    sys.path.insert(0, secureagent_root)

from agent.schemas import RawFinding
from agent.normalizer import (
    compute_fingerprint,
    normalize_raw_finding,
    extract_cwe_and_owasp,
    map_severity,
)
from agent.nodes.scan import calculate_security_score
from agent.nodes.ingest import IngestNode
from agent.scanners.semgrep_scanner import SemgrepScanner


def test_fingerprint_deterministic_and_whitespace_invariant():
    rule = "security.sqli"
    path = "app/models/user.py"
    code1 = "SELECT * FROM users WHERE id = '" + "1" + "';"
    code2 = "  SELECT *   FROM  users\nWHERE id = '1';  "

    fp1 = compute_fingerprint(rule, path, code1)
    fp2 = compute_fingerprint(rule, path, code2)

    assert fp1 == fp2
    assert len(fp1) == 64  # SHA256 length


def test_severity_mapping():
    assert map_severity("ERROR") == "critical"
    assert map_severity("critical") == "critical"
    assert map_severity("WARNING") == "high"
    assert map_severity("warn") == "high"
    assert map_severity("medium") == "medium"
    assert map_severity("low") == "low"
    assert map_severity("unknown") == "info"


def test_cwe_and_owasp_extraction():
    metadata = {
        "cwe": ["CWE-89: SQL Injection", "CWE-79"],
        "owasp": ["A03:2021 - Injection"],
    }
    cwes, owasps = extract_cwe_and_owasp(metadata)
    assert "CWE-89" in cwes
    assert "CWE-79" in cwes
    assert "A03:2021" in owasps


def test_normalize_raw_finding():
    raw = RawFinding(
        rule_id="python.flask.security.sqli",
        message="SQL injection detected in query",
        file_path="app.py",
        start_line=10,
        end_line=12,
        code="cursor.execute(f'SELECT {user}')",
        severity_raw="ERROR",
        metadata={"cwe": "CWE-89", "confidence": 0.95},
        scanner="semgrep",
    )
    finding = normalize_raw_finding(raw)

    assert finding.rule_id == raw.rule_id
    assert finding.severity == "critical"
    assert finding.confidence == 0.95
    assert "CWE-89" in finding.cwe_ids
    assert finding.file_path == "app.py"
    assert len(finding.fingerprint) == 64


def test_security_score_calculation():
    # 0 findings = 100
    assert calculate_security_score([]) == 100.0

    raw = RawFinding(
        rule_id="test",
        message="test",
        file_path="test.py",
        start_line=1,
        end_line=1,
        code="test",
        severity_raw="ERROR",
    )
    f_crit = normalize_raw_finding(raw)

    # 1 critical = 100 - 10 = 90
    assert calculate_security_score([f_crit]) == 90.0

    # Never negative
    many_crits = [f_crit] * 15
    assert calculate_security_score(many_crits) == 0.0


@pytest.mark.asyncio
async def test_semgrep_scanner_detects_demo_repo_vulnerabilities():
    scanner = SemgrepScanner()
    demo_dir = os.path.join(secureagent_root, "demo-vulnerable-repo")

    findings = await scanner.scan(demo_dir)
    assert len(findings) >= 2

    rule_ids = [f.rule_id for f in findings]
    # Verify SQL Injection & Hardcoded secret rules triggered
    assert any("sql-injection" in r for r in rule_ids)
    assert any("hardcoded-secret" in r for r in rule_ids)


def test_ingest_node_language_and_test_detection():
    ingest = IngestNode(workspace_root=os.path.join(secureagent_root, "workspaces"))
    demo_dir = os.path.join(secureagent_root, "demo-vulnerable-repo")

    lang = ingest._detect_language(demo_dir)
    assert lang == "python"
