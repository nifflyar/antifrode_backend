from dataclasses import dataclass
from datetime import datetime, UTC

from app.domain.scoring.vo import ScoringJobId
from app.domain.upload.vo import UploadId


@dataclass
class ScoringJob:
    """Represents a scoring job."""
    job_id: ScoringJobId
    upload_id: UploadId
    status: str  # PENDING, RUNNING, DONE, FAILED
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None

    def is_pending(self) -> bool:
        return self.status == "PENDING"

    def is_running(self) -> bool:
        return self.status == "RUNNING"

    def is_done(self) -> bool:
        return self.status == "DONE"

    def is_failed(self) -> bool:
        return self.status == "FAILED"

    def mark_running(self) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Cannot mark as running: status is {self.status}")
        self.status = "RUNNING"

    def mark_done(self) -> None:
        if self.status != "RUNNING":
            raise ValueError(f"Cannot mark as done: status is {self.status}")
        self.status = "DONE"
        self.finished_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        if self.status != "RUNNING":
            raise ValueError(f"Cannot mark as failed: status is {self.status}")
        self.status = "FAILED"
        self.error = error
        self.finished_at = datetime.now(UTC)
