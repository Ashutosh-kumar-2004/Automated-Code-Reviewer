"""PullRequest ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

PR_STATUS_VALUES = ("open", "merged", "closed", "draft")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repo_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # GitHub PR data
    github_pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    github_pr_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    branch_name: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)

    # Flag: at least one fix removes a hardcoded secret → PR description warns user to rotate
    has_secret_removal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="pull_requests")  # noqa: F821
    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")  # noqa: F821
    pr_fixes: Mapped[list["PrFix"]] = relationship(  # noqa: F821
        back_populates="pull_request", cascade="all, delete-orphan"
    )
