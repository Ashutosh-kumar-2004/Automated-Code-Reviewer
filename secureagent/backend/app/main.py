"""
SecureAgent FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import Base, engine
from app.middleware.rate_limit import limiter
from app.routers import auth, dashboard, findings, fixes, github, notifications, prs, reports, repos, scans, settings
from app.startup import mark_stale_scans_failed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
app_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info("SecureAgent API starting up...")
    # Create all tables (Alembic handles migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Mark stale scans as failed (crash recovery)
    await mark_stale_scans_failed()
    logger.info("Startup complete")
    yield
    logger.info("SecureAgent API shutting down...")
    await engine.dispose()


app = FastAPI(
    title="SecureAgent API",
    description="Autonomous Code Reviewer & Security Vulnerability Remediator",
    version="0.1.0",
    docs_url="/docs" if app_settings.debug else None,
    redoc_url="/redoc" if app_settings.debug else None,
    lifespan=lifespan,
)

# ── Rate limiter state ────────────────────────────────────────────────────────
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Last-Event-ID"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(github.router, prefix=API_PREFIX)
app.include_router(repos.router, prefix=API_PREFIX)
app.include_router(scans.router, prefix=API_PREFIX)
app.include_router(findings.router, prefix=API_PREFIX)
app.include_router(fixes.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(prs.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=app_settings.debug)

