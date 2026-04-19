from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from dishka.integrations.fastapi import FromDishka, inject
from typing import Optional

from app.application.dashboard.get_summary import GetDashboardSummaryInteractor
from app.application.dashboard.get_risk_trend import GetRiskTrendInteractor
from app.application.dashboard.get_risk_concentration import GetRiskConcentrationInteractor
from app.presentation.api.dashboard.schemas import (
    DashboardSummaryResponse,
    RiskTrendResponse,
    RiskConcentrationResponse
)

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@dashboard_router.get("/summary", response_model=DashboardSummaryResponse)
@inject
async def get_summary(
    interactor: FromDishka[GetDashboardSummaryInteractor],
):
    """
    Получение общих метрик по системе (кол-во пассажиров, риски, топ каналы).
    """
    return await interactor.execute()

@dashboard_router.get("/risk-trend", response_model=RiskTrendResponse)
@inject
async def get_risk_trend(
    interactor: FromDishka[GetRiskTrendInteractor],
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Получение тренда рисков по дням.
    """
    return await interactor.execute(date_from=date_from, date_to=date_to)

@dashboard_router.get("/risk-concentration", response_model=RiskConcentrationResponse)
@inject
async def get_risk_concentration(
    interactor: FromDishka[GetRiskConcentrationInteractor],
    dimension_type: str = Query(..., description="Разрез: CHANNEL, AGGREGATOR, TERMINAL, CASHDESK"),
):
    """
    Получение концентрации рисков по выбранному разрезу.
    """
    try:
        return await interactor.execute(dimension_type=dimension_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
