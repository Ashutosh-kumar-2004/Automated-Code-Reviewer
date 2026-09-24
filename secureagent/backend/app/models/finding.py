"""Finding ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Valid finding status values
FINDING_STATUS_VALUES = (
    "open",
    "fixed",
    "needs_review",
    "false_positive",
    "dismissed",
)

SEVERITY_VALUES = ("critical", "high", "medium", "low", "info")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Scanner metadata
    rule_id: Mapped[str] = mapped_column(String(512), nullable=False)
    scanner: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "semgrep"
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # De-duplication across scans
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Severity / confidence
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Location
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LLM enrichment
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    cwe_ids: Mapped[str | None] = mapped_column(Text, nullable=True)      # JSON array string
    owasp_tags: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON array string

    # Status
    status: Mapped[str] = mapped_column(
        String(32), default="open", nullable=False, index=True
    )
    false_positive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # True when the finding contains a raw secret that should be masked in the UI
    is_masked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="findings")  # noqa: F821
    fixes: Mapped[list["Fix"]] = relationship(  # noqa: F821
        back_populates="finding", cascade="all, delete-orphan", order_by="Fix.attempt_number"
    )
