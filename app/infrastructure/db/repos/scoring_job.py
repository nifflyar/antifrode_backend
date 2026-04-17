from sqlalchemy import select, update

from app.domain.scoring.entity import ScoringJob
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.scoring.vo import ScoringJobId
from app.infrastructure.db.mappers.scoring_job import ScoringJobMapper
from app.infrastructure.db.models.scoring_job import ScoringJobModel
from app.infrastructure.db.repos.base import BaseSQLAlchemyRepo


class ScoringJobRepositoryImpl(IScoringJobRepository, BaseSQLAlchemyRepo):

    async def create(self, job: ScoringJob) -> None:
        model = ScoringJobMapper.to_model(job)
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, job_id: ScoringJobId) -> ScoringJob | None:
        stmt = select(ScoringJobModel).where(ScoringJobModel.job_id == job_id.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ScoringJobMapper.to_domain(model) if model else None

    async def update(self, job: ScoringJob) -> None:
        stmt = (
            update(ScoringJobModel)
            .where(ScoringJobModel.job_id == job.job_id.value)
            .values(
                status=job.status,
                finished_at=job.finished_at,
                error=job.error,
            )
        )
        await self._session.execute(stmt)
