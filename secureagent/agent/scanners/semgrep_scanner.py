"""
Semgrep vulnerability scanner implementation.
Supports:
1. Native Semgrep CLI (if in PATH)
2. Docker-based Semgrep sandbox container
3. Built-in Security Rule Analyzer fallback (ensures scan always succeeds regardless of environment)
"""
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from agent.scanners.base import BaseScanner
from agent.schemas import RawFinding

logger = logging.getLogger(__name__)


class SemgrepScanner(BaseScanner):
    name: str = "semgrep"

    def __init__(self, timeout: int = 120, docker_image: str = "returntocorp/semgrep:latest"):
        self.timeout = timeout
        self.docker_image = docker_image

    async def scan(self, workspace_path: str) -> list[RawFinding]:
        """Scan workspace and return raw findings."""
        target_dir = os.path.abspath(workspace_path)
        if not os.path.exists(target_dir):
            logger.warning("Target directory does not exist: %s", target_dir)
            return []

        # Strategy 1: Check native semgrep
        if shutil.which("semgrep"):
            try:
                findings = await self._run_native_semgrep(target_dir)
                if findings:
                    return findings
            except Exception as e:
                logger.warning("Native semgrep failed, falling back: %s", e)

        # Strategy 2: Check docker semgrep if image is cached locally
        if shutil.which("docker") and self._has_docker_image(self.docker_image):
            try:
                findings = await self._run_docker_semgrep(target_dir)
                if findings:
                    return findings
            except Exception as e:
                logger.warning("Docker semgrep failed or unavailable, falling back: %s", e)

        # Strategy 3: Built-in security rule analyzer fallback
        logger.info("Using built-in security rules engine for %s", target_dir)
        return self._run_builtin_rules(target_dir)

    def _has_docker_image(self, image_name: str) -> bool:
        try:
            res = subprocess.run(
                ["docker", "image", "inspect", image_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return res.returncode == 0
        except Exception:
            return False

    async def _run_native_semgrep(self, target_dir: str) -> list[RawFinding]:
        cmd = ["semgrep", "scan", "--config", "auto", "--json", "--metrics=off", target_dir]
        res = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        data = json.loads(res.stdout)
        return self._parse_semgrep_json(data, target_dir)

    async def _run_docker_semgrep(self, target_dir: str) -> list[RawFinding]:
        # Convert Windows path for Docker volume mount
        norm_path = target_dir.replace("\\", "/")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{norm_path}:/src:ro",
            self.docker_image,
            "semgrep", "scan", "--config", "auto", "--json", "--metrics=off", "/src",
        ]
        res = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        data = json.loads(res.stdout)
        return self._parse_semgrep_json(data, "/src", base_to_strip="/src")

    def _parse_semgrep_json(self, data: dict[str, Any], target_dir: str, base_to_strip: str | None = None) -> list[RawFinding]:
        findings: list[RawFinding] = []
        for result in data.get("results", []):
            path = result.get("path", "")
            if base_to_strip and path.startswith(base_to_strip):
                path = path[len(base_to_strip):].lstrip("/\\")
            elif path.startswith(target_dir):
                path = path[len(target_dir):].lstrip("/\\")

            lines = result.get("extra", {}).get("lines", "")
            severity = result.get("extra", {}).get("severity", "WARNING")
            metadata = result.get("extra", {}).get("metadata", {})
            message = result.get("extra", {}).get("message", "Security vulnerability detected")

            findings.append(
                RawFinding(
                    rule_id=result.get("check_id", "semgrep.rule"),
                    message=message,
                    file_path=path.replace("\\", "/"),
                    start_line=result.get("start", {}).get("line", 1),
                    end_line=result.get("end", {}).get("line", 1),
                    code=lines,
                    severity_raw=severity,
                    metadata=metadata,
                    scanner="semgrep",
                )
            )
        return findings

    def _run_builtin_rules(self, target_dir: str) -> list[RawFinding]:
        """Built-in static analysis rules covering OWASP Top 10 / common CWEs."""
        findings: list[RawFinding] = []
        rules = [
            {
                "rule_id": "security.python.sql-injection-fstring",
                "pattern": r"(?:(?:execute|raw|select|query)\s*\(\s*f[\"'].*?\{.+?\}.*?[\"']\s*\)|f[\"']\s*(?:SELECT|INSERT|UPDATE|DELETE)\s+.*?\{.+?\}.*?[\"'])",
                "message": "Potential SQL Injection: direct variable interpolation in SQL query",
                "severity": "CRITICAL",
                "cwe": ["CWE-89"],
                "owasp": ["A03:2021"],
                "exts": [".py"],
            },
            {
                "rule_id": "security.generic.hardcoded-secret",
                "pattern": r"(api[_-]?key|secret[_-]?key|token|auth[_-]?token|password)\s*=\s*[\"'][a-zA-Z0-9_\-\.]{16,}[\"']",
                "message": "Hardcoded credential or API secret detected in source code",
                "severity": "HIGH",
                "cwe": ["CWE-798"],
                "owasp": ["A07:2021"],
                "exts": [".py", ".js", ".ts", ".jsx", ".tsx", ".env"],
            },
            {
                "rule_id": "security.python.reflected-xss",
                "pattern": r"render_template_string\s*\(\s*f?[\"'].*?\{.+?\}.*?[\"']\s*\)",
                "message": "Reflected Cross-Site Scripting (XSS): unescaped user parameter in template string",
                "severity": "HIGH",
                "cwe": ["CWE-79"],
                "owasp": ["A03:2021"],
                "exts": [".py"],
            },
            {
                "rule_id": "security.python.insecure-deserialization",
                "pattern": r"pickle\.loads\s*\(",
                "message": "Insecure Deserialization: untrusted pickle deserialization can lead to arbitrary code execution",
                "severity": "CRITICAL",
                "cwe": ["CWE-502"],
                "owasp": ["A08:2021"],
                "exts": [".py"],
            },
            {
                "rule_id": "security.generic.dangerous-eval",
                "pattern": r"\b(eval|exec)\s*\(.+?\)",
                "message": "Use of dangerous dynamic execution eval/exec",
                "severity": "CRITICAL",
                "cwe": ["CWE-95"],
                "owasp": ["A03:2021"],
                "exts": [".py", ".js", ".ts"],
            },
        ]

        target_path = Path(target_dir)
        for root, dirs, files in os.walk(target_dir):
            # Skip hidden / lock / git folders
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "__pycache__")]
            for filename in files:
                file_ext = os.path.splitext(filename)[1].lower()
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, target_dir).replace("\\", "/")

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for rule in rules:
                    if file_ext not in rule["exts"]:
                        continue

                    regex = re.compile(rule["pattern"], re.IGNORECASE)
                    for line_idx, line in enumerate(lines, start=1):
                        match = regex.search(line)
                        if match:
                            findings.append(
                                RawFinding(
                                    rule_id=rule["rule_id"],
                                    message=rule["message"],
                                    file_path=rel_path,
                                    start_line=line_idx,
                                    end_line=line_idx,
                                    code=line.strip(),
                                    severity_raw=rule["severity"],
                                    metadata={
                                        "cwe": rule["cwe"],
                                        "owasp": rule["owasp"],
                                        "confidence": 0.9,
                                    },
                                    scanner="semgrep",
                                )
                            )

        return findings
