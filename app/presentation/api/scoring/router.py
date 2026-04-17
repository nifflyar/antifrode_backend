import logging
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from dishka.integrations.fastapi import FromDishka, inject

from app.application.scoring.process_results import (
    ProcessScoringResultsInteractor,
    ProcessScoringResultsInputDTO,
)
from app.application.scoring.run_scoring import (
    RunScoringInteractor,
    RunScoringInputDTO,
)
from app.application.scoring.get_scoring_status import (
    GetScoringStatusInteractor,
    GetScoringStatusInputDTO,
)
from app.presentation.api.security import get_optional_auth_claims_from_request
from app.presentation.api.scoring.schemas import (
    ScoringRunRequest,
    ScoringRunResponse,
    ScoringStatusResponse,
)
from app.infrastructure.ml_client import (
    MLScoringResult,
    MLScoringItem,
)
from app.infrastructure.config import Config

logger = logging.getLogger(__name__)

scoring_router = APIRouter(prefix="/scoring", tags=["scoring"])


class MLScoringItemSchema(BaseModel):
    """Request schema for individual scoring item."""

    passenger_id: int
    ml_score: float
    risk_band: str
    top_reasons: list[str] = Field(default_factory=list)


class ScoringCallbackRequest(BaseModel):
    """Request schema for ML service callback."""

    job_id: str
    status: str
    results: list[MLScoringItemSchema]


class ScoringCallbackResponse(BaseModel):
    """Response schema for callback endpoint."""

    status: str
    job_id: str
    processed_passengers: int
    updated_risk_concentrations: int


@scoring_router.post("/run", response_model=ScoringRunResponse, status_code=status.HTTP_202_ACCEPTED)
@inject
async def run_scoring(
    request: Request,
    body: ScoringRunRequest,
    config: FromDishka[Config],
    interactor: FromDishka[RunScoringInteractor],
) -> ScoringRunResponse:
    """
    Start a scoring job for an upload.

    Returns immediately with job_id for status tracking.
    """
    claims = get_optional_auth_claims_from_request(request, config)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        result = await interactor(
            RunScoringInputDTO(
                upload_id=body.upload_id,
                user_id=claims.user_id.value,
            )
        )
        return ScoringRunResponse(
            job_id=result.job_id,
            status=result.status,
            started_at=result.started_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error running scoring: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@scoring_router.get("/status/{job_id}", response_model=ScoringStatusResponse)
@inject
async def get_scoring_status(
    request: Request,
    job_id: str,
    config: FromDishka[Config],
    interactor: FromDishka[GetScoringStatusInteractor],
) -> ScoringStatusResponse:
    """
    Get the status of a scoring job.
    """
    claims = get_optional_auth_claims_from_request(request, config)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        result = await interactor(GetScoringStatusInputDTO(job_id=job_id))
        return ScoringStatusResponse(
            job_id=result.job_id,
            status=result.status,
            started_at=result.started_at,
            finished_at=result.finished_at,
            error=result.error,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting scoring status: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@scoring_router.post("/callback", response_model=ScoringCallbackResponse)
@inject
async def scoring_callback(
    request: ScoringCallbackRequest,
    interactor: FromDishka[ProcessScoringResultsInteractor],
) -> ScoringCallbackResponse:
    """
    Webhook endpoint for ML service callback.

    Receives scoring results and processes them.
    """
    try:
        logger.info(
            f"Received scoring callback for job {request.job_id} "
            f"with {len(request.results)} results"
        )

        # Convert to domain models
        ml_items = [
            MLScoringItem(
                passenger_id=item.passenger_id,
                ml_score=item.ml_score,
                risk_band=item.risk_band,
                top_reasons=item.top_reasons,
            )
            for item in request.results
        ]

        ml_result = MLScoringResult(
            job_id=request.job_id,
            status=request.status,
            results=ml_items,
        )

        result = await interactor(ProcessScoringResultsInputDTO(ml_result=ml_result))

        logger.info(
            f"Scoring results processed: {result.processed_passengers} passengers, "
            f"{result.updated_risk_concentrations} risk concentrations"
        )

        return ScoringCallbackResponse(
            status="success",
            job_id=request.job_id,
            processed_passengers=result.processed_passengers,
            updated_risk_concentrations=result.updated_risk_concentrations,
        )
    except Exception as e:
        logger.error(
            f"Error processing scoring callback for job {request.job_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


