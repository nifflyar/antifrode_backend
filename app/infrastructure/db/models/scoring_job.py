from datetime import datetime

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import BaseORMModel
from app.infrastructure.db.models.types.entities import UploadIdType


class ScoringJobStatus:
    """Scoring job status constants."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ScoringJobModel(BaseORMModel):
    """Модель для хранения статуса задач скоринга."""

    __tablename__ = "scoring_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    upload_id: Mapped[int] = mapped_column(
        UploadIdType,
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ScoringJobStatus.PENDING, index=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
