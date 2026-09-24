"""PrFix join table — many-to-many between PullRequest and Fix."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PrFix(Base):
    __tablename__ = "pr_fixes"
    __table_args__ = (UniqueConstraint("pr_id", "fix_id", name="uq_pr_fix"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pr_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fix_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fixes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(back_populates="pr_fixes")  # noqa: F821
    fix: Mapped["Fix"] = relationship(back_populates="pr_fixes")  # noqa: F821
