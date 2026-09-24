"""Scan ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Valid scan status values
SCAN_STATUS_VALUES = (
    "pending",
    "cloning",
    "scanning",
    "triaging",
    "fixing",
    "verifying",
    "creating_pr",
    "completed",
    "failed",
    "cancelled",
)


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    repo_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Status
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Results
    security_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Git metadata
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # LLM usage
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scanner versions (JSON string)
    scanner_versions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="scans")  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship(  # noqa: F821
        back_populates="scan", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(  # noqa: F821
        back_populates="scan", cascade="all, delete-orphan"
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(  # noqa: F821
        back_populates="scan", cascade="all, delete-orphan", order_by="AgentLog.event_id"
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "cancelled")

    @staticmethod
    def compute_security_score(
        critical: int, high: int, medium: int, low: int
    ) -> float:
        """
        Security score formula:
          100 - (critical×10) - (high×5) - (medium×2) - (low×0.5), minimum 0
        """
        score = 100 - (critical * 10) - (high * 5) - (medium * 2) - (low * 0.5)
        return max(0.0, round(score, 1))
