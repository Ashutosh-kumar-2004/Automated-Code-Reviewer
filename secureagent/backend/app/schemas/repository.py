"""Pydantic schemas for Repository endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RepositoryPublic(BaseModel):
    id: str
    github_repo_id: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    language: str | None
    description: str | None
    is_private: bool
    is_active: bool
    last_scanned_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectRepoRequest(BaseModel):
    """Body for POST /repos — connect a GitHub repo."""
    github_repo_id: str = Field(..., description="GitHub numeric repo ID")


class GitHubRepoItem(BaseModel):
    """Represents a GitHub repo in the picker list (GET /github/repos)."""
    id: str
    full_name: str
    private: bool
    default_branch: str
    language: str | None
    description: str | None
    html_url: str
    clone_url: str
    pushed_at: str | None
    # Whether the authenticated user has push access (required to connect)
    permissions_push: bool
