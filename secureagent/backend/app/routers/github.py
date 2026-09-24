"""GitHub router — list user's GitHub repos for the repo picker."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.repository import GitHubRepoItem
from app.services.crypto import decrypt_token
from app.services.github import list_user_repos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/repos", response_model=list[GitHubRepoItem])
async def list_github_repos(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GitHubRepoItem]:
    """
    List all GitHub repositories accessible to the current user.
    Used by the frontend Connect Repo modal to let the user pick a repo.
    Only repos where the user has push permission can actually be connected.
    """
    gh_token = decrypt_token(current_user.access_token_encrypted or "")
    if not gh_token:
        return []

    raw_repos = await list_user_repos(gh_token, page=page, per_page=per_page)
    return [
        GitHubRepoItem(
            id=str(r["id"]),
            full_name=r["full_name"],
            private=r.get("private", False),
            default_branch=r.get("default_branch", "main"),
            language=r.get("language"),
            description=r.get("description"),
            html_url=r["html_url"],
            clone_url=r["clone_url"],
            pushed_at=r.get("pushed_at"),
            permissions_push=r.get("permissions", {}).get("push", False),
        )
        for r in raw_repos
    ]
