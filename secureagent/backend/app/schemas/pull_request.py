"""PullRequest Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PullRequestBase(BaseModel):
    branch_name: str
    title: str
    body: str | None = None
    status: str = "open"


class CreatePullRequestRequest(BaseModel):
    scan_id: str
    title: str | None = None
    body: str | None = None


class PullRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    repo_id: str
    repo_name: str | None = None
    repo_url: str | None = None
    github_pr_number: int | None = None
    github_pr_url: str | None = None
    branch_name: str
    title: str
    body: str | None = None
    status: str
    has_secret_removal: bool = False
    fixes_count: int = 0
    created_at: datetime
    merged_at: datetime | None = None
    updated_at: datetime | None = None


class RefreshPullRequestResponse(BaseModel):
    status: str
    merged_at: datetime | None = None
    message: str
