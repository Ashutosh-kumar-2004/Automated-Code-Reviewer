"""Fix ORM model — one row per LLM fix attempt."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

FIX_STATUS_VALUES = (
    "pending",
    "applied",
    "verified",
    "failed",
    "approved",
    "rejected",
)


class Fix(Base):
    __tablename__ = "fixes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Patch content
    patch_diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw structured JSON from the LLM (before diff generation)
    replacement_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verify_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM metadata
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # JSON list of relative file paths touched
    files_changed: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Human approval
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user.id
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    finding: Mapped["Finding"] = relationship(back_populates="fixes")  # noqa: F821
    pr_fixes: Mapped[list["PrFix"]] = relationship(  # noqa: F821
        back_populates="fix", cascade="all, delete-orphan"
    )
