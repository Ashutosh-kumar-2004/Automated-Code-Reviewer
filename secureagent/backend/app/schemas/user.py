"""
Pydantic schemas for User and auth endpoints.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    """Safe user representation — never include access_token_encrypted."""
    id: str
    github_id: str
    login: str
    email: str | None
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthValidateRequest(BaseModel):
    """
    Payload sent by the Next.js BFF when a user first logs in.
    The BFF extracts these fields from the NextAuth session.
    """
    github_id: str = Field(..., description="GitHub numeric user ID")
    login: str = Field(..., description="GitHub username")
    email: str | None = None
    avatar_url: str | None = None
    access_token: str = Field(..., description="GitHub OAuth access token (will be encrypted)")


class AuthValidateResponse(BaseModel):
    user: UserPublic
    is_new_user: bool
