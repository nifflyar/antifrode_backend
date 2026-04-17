from fastapi import APIRouter, HTTPException, status, Query
from datetime import datetime
from dishka.integrations.fastapi import FromDishka, inject
import logging

from app.application.dashboard.get_summary import (
    GetDashboardSummaryInteractor,
    GetDashboardSummaryInputDTO,
)
from app.application.dashboard.get_risk_trend import (
    GetRiskTrendInteractor,
    GetRiskTrendInputDTO,
)
from app.application.dashboard.get_risk_concentration import (
    GetRiskConcentrationInteractor,
    GetRiskConcentrationInputDTO,
)
from app.presentation.api.dashboard.schemas import (
    DashboardSummaryResponse,
    RiskTrendResponse,
    RiskConcentrationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
@inject
async def get_dashboard_summary(
    interactor: FromDishka[GetDashboardSummaryInteractor],
) -> DashboardSummaryResponse:
    """Get dashboard summary with key metrics."""
    try:
        result = await interactor(GetDashboardSummaryInputDTO())
        return DashboardSummaryResponse(
            total_passengers=result.total_passengers,
            high_risk_count=result.high_risk_count,
            critical_risk_count=result.critical_risk_count,
            share_suspicious_ops=result.share_suspicious_ops,
            top_risk_channel=result.top_risk_channel,
            top_risk_terminal=result.top_risk_terminal,
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard summary: {str(e)}",
        )


@router.get("/risk-trend", response_model=RiskTrendResponse)
@inject
async def get_risk_trend(
    date_from: str | None = Query(None, description="Start date (ISO format)"),
    date_to: str | None = Query(None, description="End date (ISO format)"),
    interactor: FromDishka[GetRiskTrendInteractor] = None,
) -> RiskTrendResponse:
    """Get risk trends over time."""
    try:
        # Parse date strings to datetime objects
        date_from_dt = None
        date_to_dt = None
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from)
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to)

        result = await interactor(
            GetRiskTrendInputDTO(
                date_from=date_from_dt,
                date_to=date_to_dt,
            )
        )
        return RiskTrendResponse(trends=result.trends)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error fetching risk trend: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk trend",
        )


@router.get("/risk-concentration", response_model=RiskConcentrationResponse)
@inject
async def get_risk_concentration(
    dimension_type: str = Query(
        ..., description="Dimension type: channel, aggregator, terminal, cashdesk, point_of_sale"
    ),
    interactor: FromDishka[GetRiskConcentrationInteractor] = None,
) -> RiskConcentrationResponse:
    """Get risk concentration analysis by dimension."""
    try:
        result = await interactor(
            GetRiskConcentrationInputDTO(dimension_type=dimension_type)
        )
        return RiskConcentrationResponse(items=result.items)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching risk concentration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk concentration",
        )


dashboard_router = router
