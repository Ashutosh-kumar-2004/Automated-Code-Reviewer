"""
IngestNode — Clones the repository securely and performs environment analysis.
Enforces clone hygiene:
- Disables hooks via core.hooksPath=/dev/null
- Disables submodules
- Purges access token from git remote immediately after clone
- Detects language and test runner
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from agent.state import AgentState

logger = logging.getLogger(__name__)


class IngestNode:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        os.makedirs(workspace_root, exist_ok=True)

    async def run(self, state: AgentState, token: str | None = None) -> AgentState:
        """Execute ingestion on the target repository."""
        repo_url = state["repo_url"]
        scan_id = state["scan_id"]

        scan_workspace = os.path.join(self.workspace_root, scan_id)
        if os.path.exists(scan_workspace):
            shutil.rmtree(scan_workspace, ignore_errors=True)
        os.makedirs(scan_workspace, exist_ok=True)

        logger.info("Cloning %s into workspace %s", repo_url, scan_workspace)

        # Clone repository
        if repo_url.startswith("http://") or repo_url.startswith("https://"):
            env = os.environ.copy()
            env["GIT_CONFIG_NOSYSTEM"] = "1"
            env["GIT_TERMINAL_PROMPT"] = "0"

            target_url = repo_url
            if token and "github.com" in repo_url:
                target_url = repo_url.replace("https://github.com", f"https://x-access-token:{token}@github.com")

            clone_cmd = [
                "git", "clone",
                "--depth=1",
                "--no-local",
                "--config", "core.hooksPath=/dev/null",
                "--no-recurse-submodules",
                target_url,
                scan_workspace,
            ]

            res = await asyncio.to_thread(
                subprocess.run,
                clone_cmd,
                env=env,
                capture_output=True,
                text=True,
            )

            if res.returncode != 0:
                err_msg = res.stderr or res.stdout or "Unknown git error"
                logger.error("Git clone failed: %s", err_msg)
                state["error"] = f"Clone failed: {err_msg}"
                state["status"] = "failed"
                return state

            # Purge token from git config by blanking the remote
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    ["git", "remote", "set-url", "origin", ""],
                    cwd=scan_workspace,
                    capture_output=True,
                )
            except Exception as e:
                logger.warning("Failed to reset remote URL: %s", e)

        elif os.path.isdir(repo_url):
            # Local directory (e.g. demo-vulnerable-repo)
            for item in os.listdir(repo_url):
                if item == ".git":
                    continue
                s = os.path.join(repo_url, item)
                d = os.path.join(scan_workspace, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

        state["workspace_dir"] = scan_workspace
        state["detected_language"] = self._detect_language(scan_workspace)
        state["test_runner"] = self._detect_test_runner(scan_workspace)
        state["status"] = "cloned"
        return state

    def _detect_language(self, path: str) -> str:
        ext_counts: dict[str, int] = {}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv")]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in (".py", ".js", ".ts", ".go", ".java", ".rs"):
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if not ext_counts:
            return "python"

        top_ext = max(ext_counts, key=ext_counts.get)
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
        }
        return lang_map.get(top_ext, "python")

    def _detect_test_runner(self, path: str) -> str | None:
        p = Path(path)
        if (p / "pytest.ini").exists() or (p / "pyproject.toml").exists() or (p / "setup.cfg").exists():
            return "pytest"
        if (p / "package.json").exists():
            try:
                with open(p / "package.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "test" in data.get("scripts", {}):
                        return "npm test"
            except Exception:
                pass
        return None
