"""AgentLog ORM model — append-only event log for SSE streaming and audit."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    scan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Monotonically increasing integer per scan — used for SSE Last-Event-ID replay
    event_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(16), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON blob for structured metadata (finding_id, attempt, pct_complete, etc.)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="agent_logs")  # noqa: F821
