from app.domain.scoring.entity import ScoringJob
from app.domain.scoring.vo import ScoringJobId
from app.infrastructure.db.models.scoring_job import ScoringJobModel


class ScoringJobMapper:
    @staticmethod
    def to_domain(model: ScoringJobModel) -> ScoringJob:
        return ScoringJob(
            job_id=ScoringJobId(model.job_id),
            upload_id=model.upload_id,
            status=model.status,
            started_at=model.started_at,
            finished_at=model.finished_at,
            error=model.error,
        )

    @staticmethod
    def to_model(job: ScoringJob) -> ScoringJobModel:
        return ScoringJobModel(
            job_id=job.job_id.value,
            upload_id=job.upload_id.value,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
        )
