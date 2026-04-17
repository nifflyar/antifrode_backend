import logging
from dataclasses import dataclass
from datetime import datetime

from app.application.common.interactor import Interactor
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.scoring.vo import ScoringJobId

logger = logging.getLogger(__name__)


@dataclass
class GetScoringStatusInputDTO:
    """Input for getting scoring status."""
    job_id: str


@dataclass
class GetScoringStatusOutputDTO:
    """Output from getting scoring status."""
    job_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    error: str | None


class GetScoringStatusInteractor(Interactor[GetScoringStatusInputDTO, GetScoringStatusOutputDTO]):
    """Get the status of a scoring job."""

    def __init__(
        self,
        scoring_job_repository: IScoringJobRepository,
    ):
        self.scoring_job_repository = scoring_job_repository

    async def __call__(self, data: GetScoringStatusInputDTO) -> GetScoringStatusOutputDTO:
        """Get scoring job status."""

        job = await self.scoring_job_repository.get_by_id(ScoringJobId(data.job_id))

        if not job:
            raise ValueError(f"Scoring job {data.job_id} not found")

        return GetScoringStatusOutputDTO(
            job_id=job.job_id.value,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
        )
