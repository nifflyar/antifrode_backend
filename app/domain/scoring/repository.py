from abc import ABC, abstractmethod
from app.domain.scoring.entity import ScoringJob
from app.domain.scoring.vo import ScoringJobId


class IScoringJobRepository(ABC):
    """Repository for scoring jobs."""

    @abstractmethod
    async def create(self, job: ScoringJob) -> None:
        """Create a new scoring job."""
        ...

    @abstractmethod
    async def get_by_id(self, job_id: ScoringJobId) -> ScoringJob | None:
        """Get a scoring job by ID."""
        ...

    @abstractmethod
    async def update(self, job: ScoringJob) -> None:
        """Update an existing scoring job."""
        ...
