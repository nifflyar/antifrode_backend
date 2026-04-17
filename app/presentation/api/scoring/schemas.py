from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ScoringRunRequest(BaseModel):
    """Request to run scoring."""
    upload_id: int


class ScoringRunResponse(BaseModel):
    """Response from running scoring."""
    job_id: str
    status: str
    started_at: datetime


class ScoringStatusResponse(BaseModel):
    """Response with scoring job status."""
    job_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
