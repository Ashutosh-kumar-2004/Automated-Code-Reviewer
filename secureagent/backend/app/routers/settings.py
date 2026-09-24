"""Settings router — get and update user preferences."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class UserSettingsPublic(BaseModel):
    auto_open_pr: bool
    severity_threshold: str
    enabled_scanners: str
    auto_fix_severities: str
    max_findings_to_fix: int
    max_patch_lines: int
    confidence_threshold: float
    llm_triage_model: str | None
    llm_fix_model: str | None

    model_config = {"from_attributes": True}


class UpdateSettingsRequest(BaseModel):
    auto_open_pr: bool | None = None
    severity_threshold: str | None = None
    enabled_scanners: str | None = None
    auto_fix_severities: str | None = None
    max_findings_to_fix: int | None = None
    max_patch_lines: int | None = None
    confidence_threshold: float | None = None
    llm_triage_model: str | None = None
    llm_fix_model: str | None = None


@router.get("", response_model=UserSettingsPublic)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsPublic:
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        # Create defaults if missing
        settings_row = UserSettings(user_id=current_user.id)
        db.add(settings_row)
        await db.commit()
        await db.refresh(settings_row)
    return UserSettingsPublic.model_validate(settings_row)


@router.put("", response_model=UserSettingsPublic)
async def update_settings(
    body: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSettingsPublic:
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db.add(settings_row)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(settings_row, field, value)

    await db.commit()
    await db.refresh(settings_row)
    return UserSettingsPublic.model_validate(settings_row)
