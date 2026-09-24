"""
GitHub service — thin wrapper around the GitHub REST API v3.
Uses the authenticated user's decrypted access token.
"""
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def _gh_get(path: str, token: str, params: dict | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(base_url=settings.github_api_base) as client:
        resp = await client.get(path, headers=headers, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()


async def list_user_repos(token: str, page: int = 1, per_page: int = 100) -> list[dict]:
    """Return repos the authenticated user can access."""
    return await _gh_get(
        "/user/repos",
        token,
        params={"sort": "pushed", "per_page": per_page, "page": page},
    )


async def get_repo(token: str, owner: str, repo: str) -> dict:
    """Fetch a single repo by owner/name."""
    return await _gh_get(f"/repos/{owner}/{repo}", token)


async def get_repo_by_id(token: str, repo_id: str) -> dict | None:
    """
    GitHub doesn't expose a direct GET /repositories/{id} with user token scoped search,
    so we list repos and find by id. For efficiency we search across pages (max 3).
    """
    for page in range(1, 4):
        repos = await list_user_repos(token, page=page)
        if not repos:
            break
        for r in repos:
            if str(r["id"]) == str(repo_id):
                return r
    return None


async def check_push_permission(token: str, full_name: str) -> bool:
    """
    Verify the authenticated user has PUSH permission on the given repo.
    Required before connecting a repo to SecureAgent.
    """
    try:
        data = await _gh_get(f"/repos/{full_name}", token)
        perms = data.get("permissions", {})
        return bool(perms.get("push", False))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (403, 404):
            return False
        raise
