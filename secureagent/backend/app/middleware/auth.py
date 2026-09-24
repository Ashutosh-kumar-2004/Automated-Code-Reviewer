"""
Auth middleware: validate HS256 JWT minted by the Next.js BFF.

JWT payload structure:
  {
    "sub": "<user_id>",
    "github_id": "<github_id>",
    "login": "<github_login>",
    "iat": <issued_at>,
    "exp": <expires_at>
  }

The token is signed with BACKEND_SECRET (shared between BFF and FastAPI).
FastAPI never issues tokens itself; it only validates.
"""
import json
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.finding import Finding
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User

settings = get_settings()

ALGORITHM = "HS256"


def _extract_bearer(request: Request) -> str:
    """Pull Bearer token from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    return auth[len("Bearer "):]


def decode_bff_token(token: str) -> dict[str, Any]:
    """Decode and validate the BFF-issued HS256 JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.backend_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc
    return payload


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: validate BFF JWT → return the User ORM object.
    Raises 401 if token is invalid, 404 if user not found.
    """
    token = _extract_bearer(request)
    payload = decode_bff_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing sub")

    result = await db.execute(
        select(User).where((User.id == user_id) | (User.github_id == user_id))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ── IDOR helpers ─────────────────────────────────────────────────────────────
# Every helper performs the ownership chain check:
#   resource → repository → user_id == current_user.id


async def get_owned_repo(
    repo_id: str,
    current_user: User,
    db: AsyncSession,
) -> Repository:
    """Return the Repository iff it belongs to current_user; else 403/404."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    if repo.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return repo


async def get_owned_scan(
    scan_id: str,
    current_user: User,
    db: AsyncSession,
) -> Scan:
    """Return the Scan iff its repo belongs to current_user; else 403/404."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    await get_owned_repo(scan.repo_id, current_user, db)
    return scan


async def get_owned_finding(
    finding_id: str,
    current_user: User,
    db: AsyncSession,
) -> Finding:
    """Return the Finding iff its scan's repo belongs to current_user; else 403/404."""
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    await get_owned_scan(finding.scan_id, current_user, db)
    return finding
