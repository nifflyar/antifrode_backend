import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import uuid4

from app.application.common.interactor import Interactor
from app.application.common.transaction import TransactionManager
from app.domain.audit.entity import AuditLog
from app.domain.audit.repository import IAuditLogRepository
from app.domain.scoring.entity import ScoringJob
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.scoring.vo import ScoringJobId
from app.domain.upload.vo import UploadId
from app.domain.user.vo import UserId

logger = logging.getLogger(__name__)


@dataclass
class RunScoringInputDTO:
    """Input for running scoring."""
    upload_id: int
    user_id: int


@dataclass
class RunScoringOutputDTO:
    """Output from running scoring."""
    job_id: str
    status: str
    started_at: datetime


class RunScoringInteractor(Interactor[RunScoringInputDTO, RunScoringOutputDTO]):
    """Create and start a scoring job."""

    def __init__(
        self,
        scoring_job_repository: IScoringJobRepository,
        audit_log_repository: IAuditLogRepository,
        transaction_manager: TransactionManager,
    ):
        self.scoring_job_repository = scoring_job_repository
        self.audit_log_repository = audit_log_repository
        self.transaction_manager = transaction_manager

    async def __call__(self, data: RunScoringInputDTO) -> RunScoringOutputDTO:
        """Create a scoring job and log the action."""

        # Create job_id
        job_id = str(uuid4())
        now = datetime.now(UTC)

        # Create scoring job entity
        job = ScoringJob(
            job_id=ScoringJobId(job_id),
            upload_id=UploadId(data.upload_id),
            status="PENDING",
            started_at=now,
        )

        # Save to repository
        await self.scoring_job_repository.create(job)

        # Log audit event
        audit_log = AuditLog.create(
            log_id=str(uuid4()),
            user_id=UserId(data.user_id),
            action="SCORING_STARTED",
            entity_type="scoring_job",
            entity_id=job_id,
            meta={
                "upload_id": data.upload_id,
                "job_id": job_id,
            },
        )
        await self.audit_log_repository.create_audit_log(audit_log)

        # Commit transaction
        await self.transaction_manager.commit()

        logger.info(f"Created scoring job {job_id} for upload {data.upload_id}")

        return RunScoringOutputDTO(
            job_id=job_id,
            status="PENDING",
            started_at=now,
        )
