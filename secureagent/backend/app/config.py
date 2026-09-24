"""
Application configuration using pydantic-settings.
All values are read from environment variables / .env file.
"""
import os
import tempfile
from functools import lru_cache
from typing import Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "SecureAgent"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ── Database ─────────────────────────────────────────────────────────────
    # Local SQLite default; overridden in production by cloud DB (Turso / Postgres)
    database_url: str = "sqlite+aiosqlite:///./secureagent.db"
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # ── Redis / Celery (Phase 6) ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    # Shared HS256 secret between Next.js BFF and FastAPI
    backend_secret: str = "CHANGE_ME_32_CHARS_MIN_BACKEND_SECRET"
    # JWT expiry for BFF-minted tokens (seconds)
    jwt_expiry_seconds: int = 600  # 10 minutes
    # Fernet key for encrypting GitHub access tokens at rest
    encryption_key: str = ""

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_client_id: str = ""
    github_client_secret: str = ""
    github_api_base: str = "https://api.github.com"

    # ── Frontend (CORS allowlist) ─────────────────────────────────────────────
    # Frontend URL (e.g. https://your-app.vercel.app or http://localhost:3000)
    frontend_url: str = "http://localhost:3000"
    # Optional additional comma-separated CORS origins
    cors_origins: str = ""

    # ── Workspace ─────────────────────────────────────────────────────────────
    # Default to cross-platform temporary directory; override via WORKSPACE_ROOT in .env
    workspace_root: str = os.path.join(tempfile.gettempdir(), "secureagent", "workspaces")

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = "google"
    llm_triage_model: str = "gemini-3.6-flash"
    llm_fix_model: str = "gemini-3.6-flash"
    google_api_key: str = ""

    # ── Scan Limits ───────────────────────────────────────────────────────────
    max_repo_size_mb: int = 100
    max_files_to_scan: int = 1000
    max_llm_tokens_per_scan: int = 200_000
    max_findings_to_fix: int = 10
    max_patch_lines: int = 200
    confidence_threshold: float = 0.7
    auto_fix_severities: str = "critical,high,medium"
    max_fix_attempts: int = 3

    # ── Concurrency & Timeouts ────────────────────────────────────────────────
    max_concurrent_scans: int = 10
    scan_timeout_total: int = 1800  # 30 minutes

    # ── Remediation Notifications ─────────────────────────────────────────────
    # Duration between notifications when vulnerabilities are present (minutes, default 60 = 1 hour)
    remediation_notification_interval_minutes: int = 60

    # ── Scanners ──────────────────────────────────────────────────────────────
    semgrep_timeout: int = 120
    sandbox_image: str = "secureagent-sandbox:latest"
    sandbox_cpu: str = "0.5"
    sandbox_memory: str = "512m"
    sandbox_timeout: int = 120

    @property
    def auto_fix_severities_list(self) -> list[str]:
        return [s.strip() for s in self.auto_fix_severities.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        origins: set[str] = set()
        for raw in [self.frontend_url, self.cors_origins]:
            if raw:
                for part in raw.split(","):
                    p = part.strip().rstrip("/")
                    if p:
                        origins.add(p)
        if not origins:
            origins.add("http://localhost:3000")
        return list(origins)

    @property
    def resolved_database_url(self) -> str:
        """
        Returns the appropriate database URL based on the environment:
        - In development: defaults to local SQLite file (./secureagent.db)
        - In production: uses TURSO_DATABASE_URL or DATABASE_URL provided by cloud deployment
        """
        if self.environment == "development":
            return "sqlite+aiosqlite:///./secureagent.db"

        # In production:
        if self.turso_database_url and self.turso_database_url.strip() and "yourname" not in self.turso_database_url:
            url = self.turso_database_url.strip()
            if not url.startswith("sqlite+"):
                url = f"sqlite+{url}"
            return url

        if self.database_url and self.database_url.strip():
            return self.database_url.strip()

        return "sqlite+aiosqlite:///./secureagent.db"




@lru_cache
def get_settings() -> Settings:
    return Settings()
