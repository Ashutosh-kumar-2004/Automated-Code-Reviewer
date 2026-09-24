"""UserSettings ORM model — one-to-one with User."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # PR behaviour
    auto_open_pr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Scan configuration
    severity_threshold: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    enabled_scanners: Mapped[str] = mapped_column(String(512), default="semgrep", nullable=False)
    auto_fix_severities: Mapped[str] = mapped_column(
        String(128), default="critical,high,medium", nullable=False
    )
    max_findings_to_fix: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_patch_lines: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    # LLM models (overrides global env)
    llm_triage_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_fix_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="settings")  # noqa: F821
