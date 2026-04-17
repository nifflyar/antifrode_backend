import logging
from dataclasses import dataclass
from datetime import datetime, UTC

from app.application.common.interactor import Interactor
from app.application.common.transaction import TransactionManager
from app.application.scoring.process_results import ProcessScoringResultsInteractor
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.scoring.vo import ScoringJobId
from app.infrastructure.ml_client import MlServiceClient, MLScoringResult

logger = logging.getLogger(__name__)


@dataclass
class ExecuteScoringInputDTO:
    """Input for executing scoring."""
    job_id: str
    upload_id: int


@dataclass
class ExecuteScoringOutputDTO:
    """Output from executing scoring."""
    job_id: str
    status: str
    processed_passengers: int


class ExecuteScoringInteractor(Interactor[ExecuteScoringInputDTO, ExecuteScoringOutputDTO]):
    """Execute ML scoring and process results."""

    def __init__(
        self,
        ml_client: MlServiceClient,
        process_results_interactor: ProcessScoringResultsInteractor,
        scoring_job_repository: IScoringJobRepository,
        transaction_manager: TransactionManager,
    ):
        self.ml_client = ml_client
        self.process_results_interactor = process_results_interactor
        self.scoring_job_repository = scoring_job_repository
        self.transaction_manager = transaction_manager

    async def __call__(self, data: ExecuteScoringInputDTO) -> ExecuteScoringOutputDTO:
        """Execute scoring and process results."""

        try:
            # Run ML scoring
            logger.info(f"Starting ML scoring for job {data.job_id}, upload {data.upload_id}")
            await self.ml_client.run_scoring(data.upload_id)

            # Get results
            ml_result: MLScoringResult = await self.ml_client.get_scoring_result(
                data.job_id, data.upload_id
            )

            # Update job status
            job = await self.scoring_job_repository.get_by_id(ScoringJobId(data.job_id))
            if job:
                job.status = "PROCESSING_RESULTS"
                await self.scoring_job_repository.update(job)

            # Process results (save to database)
            from app.application.scoring.process_results import ProcessScoringResultsInputDTO
            results_output = await self.process_results_interactor(
                ProcessScoringResultsInputDTO(ml_result=ml_result)
            )

            # Mark job as completed
            job = await self.scoring_job_repository.get_by_id(ScoringJobId(data.job_id))
            if job:
                job.status = "COMPLETED"
                await self.scoring_job_repository.update(job)

            await self.transaction_manager.commit()

            logger.info(
                f"✅ Scoring completed for job {data.job_id}: "
                f"{results_output.processed_passengers} passengers processed"
            )

            return ExecuteScoringOutputDTO(
                job_id=data.job_id,
                status="COMPLETED",
                processed_passengers=results_output.processed_passengers,
            )

        except Exception as e:
            logger.error(f"❌ Scoring failed for job {data.job_id}: {e}")

            # Mark job as failed
            job = await self.scoring_job_repository.get_by_id(ScoringJobId(data.job_id))
            if job:
                job.status = "FAILED"
                await self.scoring_job_repository.update(job)

            await self.transaction_manager.commit()
            raise
