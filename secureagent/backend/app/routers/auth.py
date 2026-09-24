"""
Auth router — called by the Next.js BFF on every session establishment.

POST /api/v1/auth/validate
  Body: { github_id, login, email, avatar_url, access_token }
  Upserts the user; encrypts and stores the access token.

GET /api/v1/auth/me
  Returns the current authenticated user.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.user import AuthValidateRequest, AuthValidateResponse, UserPublic
from app.services.crypto import encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/validate", response_model=AuthValidateResponse)
async def validate_and_upsert_user(
    body: AuthValidateRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthValidateResponse:
    """
    Called by BFF after GitHub OAuth completes.
    Creates a new user or updates an existing one.
    Encrypts the GitHub access token before storage.
    """
    result = await db.execute(
        select(User).where(User.github_id == body.github_id)
    )
    user = result.scalar_one_or_none()
    is_new_user = user is None

    encrypted = encrypt_token(body.access_token)

    if is_new_user:
        user = User(
            github_id=body.github_id,
            login=body.login,
            email=body.email,
            avatar_url=body.avatar_url,
            access_token_encrypted=encrypted,
        )
        db.add(user)
        await db.flush()  # get the generated ID

        # Create default settings for new user
        settings_row = UserSettings(user_id=user.id)
        db.add(settings_row)
        logger.info("Created new user: %s (%s)", body.login, body.github_id)
    else:
        # Update mutable fields
        user.login = body.login
        user.email = body.email
        user.avatar_url = body.avatar_url
        user.access_token_encrypted = encrypted
        logger.info("Updated existing user: %s", body.login)

    await db.commit()
    await db.refresh(user)
    return AuthValidateResponse(user=UserPublic.model_validate(user), is_new_user=is_new_user)


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """Return the currently authenticated user."""
    return UserPublic.model_validate(current_user)
