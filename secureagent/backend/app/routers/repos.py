"""
Repos router — list, connect, disconnect repositories.
POST /repos verifies the user has push permission via GitHub API before connecting.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_owned_repo
from app.models.repository import Repository
from app.models.scan import Scan
from app.models.user import User
from app.schemas.repository import ConnectRepoRequest, RepositoryPublic
from app.schemas.scan import ScanPublic
from app.services.crypto import decrypt_token
from app.services.github import check_push_permission, get_repo_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["repositories"])


@router.get("", response_model=list[RepositoryPublic])
async def list_repos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RepositoryPublic]:
    """List all repos connected by the current user."""
    result = await db.execute(
        select(Repository)
        .where(Repository.user_id == current_user.id, Repository.is_active == True)  # noqa: E712
        .order_by(Repository.created_at.desc())
    )
    repos = result.scalars().all()
    return [RepositoryPublic.model_validate(r) for r in repos]


@router.post("", response_model=RepositoryPublic, status_code=status.HTTP_201_CREATED)
async def connect_repo(
    body: ConnectRepoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryPublic:
    """
    Connect a GitHub repo to SecureAgent.
    Verifies:
      1. The user's token is valid and decryptable.
      2. The repo exists and the user has PUSH permission.
      3. The repo isn't already connected by this user.
    """
    # 1. Decrypt user's GitHub token
    gh_token = decrypt_token(current_user.access_token_encrypted or "")
    if not gh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub token unavailable — please re-authenticate",
        )

    # 2. Fetch repo from GitHub and verify push permission
    gh_repo = await get_repo_by_id(gh_token, body.github_repo_id)
    if gh_repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found on GitHub or not accessible",
        )

    has_push = await check_push_permission(gh_token, gh_repo["full_name"])
    if not has_push:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have push (write) permission on the repository to connect it",
        )

    # 3. Check not already connected
    existing = await db.execute(
        select(Repository).where(
            Repository.user_id == current_user.id,
            Repository.github_repo_id == str(gh_repo["id"]),
            Repository.is_active == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This repository is already connected",
        )

    repo = Repository(
        user_id=current_user.id,
        github_repo_id=str(gh_repo["id"]),
        full_name=gh_repo["full_name"],
        clone_url=gh_repo["clone_url"],
        html_url=gh_repo["html_url"],
        default_branch=gh_repo.get("default_branch", "main"),
        language=gh_repo.get("language"),
        description=gh_repo.get("description"),
        is_private=gh_repo.get("private", False),
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    logger.info("User %s connected repo %s", current_user.login, repo.full_name)
    return RepositoryPublic.model_validate(repo)


@router.get("/{repo_id}", response_model=RepositoryPublic)
async def get_repo_detail(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryPublic:
    repo = await get_owned_repo(repo_id, current_user, db)
    return RepositoryPublic.model_validate(repo)


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_repo(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = await get_owned_repo(repo_id, current_user, db)
    repo.is_active = False
    await db.commit()
    logger.info("User %s disconnected repo %s", current_user.login, repo.full_name)


@router.get("/{repo_id}/scans", response_model=list[ScanPublic])
async def list_repo_scans(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScanPublic]:
    repo = await get_owned_repo(repo_id, current_user, db)
    result = await db.execute(
        select(Scan)
        .where(Scan.repo_id == repo.id)
        .order_by(Scan.started_at.desc())
        .limit(50)
    )
    scans = result.scalars().all()
    return [ScanPublic.model_validate(s) for s in scans]
