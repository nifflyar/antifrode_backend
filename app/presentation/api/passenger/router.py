from fastapi import APIRouter, HTTPException, Query, Depends, Request
from dishka.integrations.fastapi import FromDishka, inject
from typing import Optional
from dataclasses import asdict

from app.domain.passenger.vo import RiskBand
from app.application.passenger.list_passengers import ListPassengersInteractor
from app.application.passenger.get_passenger_profile import GetPassengerProfileInteractor
from app.application.passenger.get_passenger_transactions import GetPassengerTransactionsInteractor
from app.application.passenger.override_risk import OverridePassengerRiskInteractor, OverrideRiskInput
from app.presentation.api.passenger.schemas import (
    PassengerListResponse,
    PassengerProfileResponse,
    PassengerTransactionSchema,
    PassengerListItemSchema,
    RiskOverrideRequest
)

passenger_router = APIRouter(prefix="/passengers", tags=["Passengers"])

@passenger_router.get("/", response_model=PassengerListResponse)
@inject
async def list_passengers(
    interactor: FromDishka[ListPassengersInteractor],
    risk_band: Optional[RiskBand] = Query(None),
    search: Optional[str] = Query(None, description="Поиск по ФИО или ИИН"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Получение списка пассажиров с фильтрацией по риску и поиском.
    """
    result = await interactor.execute(
        risk_band=risk_band,
        search=search,
        limit=limit,
        offset=offset
    )
    
    # Маппинг для упрощенного списка
    items = []
    for p in result.items:
        items.append(PassengerListItemSchema(
            id=str(p.id.value),
            fio_clean=p.fio_clean,
            fake_fio_score=p.fake_fio_score,
            last_seen_at=p.last_seen_at,
            risk_band=p.score.risk_band if p.score else RiskBand.low,
            final_score=p.score.final_score if p.score else 0.0,
            top_reasons=p.score.top_reasons if p.score and p.score.top_reasons else [],
            refund_cnt=p.features.refund_cnt if p.features else 0,
            max_tickets_month=p.features.max_tickets_month if p.features else 0,
            seat_blocking_flag=p.score.seat_blocking_flag if p.score else False
        ))
        
    return PassengerListResponse(
        items=items,
        total=result.total,
        limit=result.limit,
        offset=result.offset
    )

@passenger_router.get("/{passenger_id}", response_model=PassengerProfileResponse)
@inject
async def get_passenger(
    passenger_id: int,
    interactor: FromDishka[GetPassengerProfileInteractor],
):
    """
    Получение детального профиля пассажира (баллы, признаки).
    """
    passenger = await interactor.execute(passenger_id)
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")

    # Manually construct response to handle enum serialization
    features_dict = asdict(passenger.features) if passenger.features else None
    score_dict = None
    if passenger.score:
        score_dict = asdict(passenger.score)
        # Convert RiskBand enum to its string value
        if hasattr(score_dict.get('risk_band'), 'value'):
            score_dict['risk_band'] = score_dict['risk_band'].value
        elif isinstance(score_dict.get('risk_band'), str):
            pass  # Already a string
        else:
            score_dict['risk_band'] = str(passenger.score.risk_band)

    return PassengerProfileResponse(
        id=str(passenger.id.value),
        fio_clean=passenger.fio_clean,
        fake_fio_score=passenger.fake_fio_score,
        first_seen_at=passenger.first_seen_at,
        last_seen_at=passenger.last_seen_at,
        features=features_dict,
        score=score_dict
    )

@passenger_router.get("/{passenger_id}/transactions", response_model=list[PassengerTransactionSchema])
@inject
async def get_passenger_transactions(
    passenger_id: int,
    interactor: FromDishka[GetPassengerTransactionsInteractor],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    История транзакций конкретного пассажира.
    """
    transactions = await interactor.execute(passenger_id, limit, offset)
    
    return [
        PassengerTransactionSchema(
            id=str(tx.id.value),
            op_type=tx.op_type.value,
            op_datetime=tx.op_datetime,
            dep_datetime=tx.dep_datetime,
            train_no=tx.train_no,
            amount=tx.amount,
            fee=tx.fee,
            channel=tx.channel,
            route=tx.route,
            fio=tx.fio,
            iin=tx.iin,
            phone=tx.phone,
            doc_no=tx.doc_no,
            order_no=tx.order_no,
            dep_station=tx.dep_station,
            arr_station=tx.arr_station,
            terminal=tx.terminal,
            cashdesk=tx.cashdesk,
            aggregator=tx.aggregator,
            point_of_sale=tx.point_of_sale,
            tariff_type=tx.tariff_type,
            service_class=tx.service_class,
            gender=tx.gender,
            branch=tx.branch,
            carrier=tx.carrier,
            settlement_type=tx.settlement_type
        )
        for tx in transactions
    ]

@passenger_router.post("/{passenger_id}/override")
@inject
async def override_risk(
    request: Request,
    passenger_id: int,
    data: RiskOverrideRequest,
    interactor: FromDishka[OverridePassengerRiskInteractor],
):
    claims = getattr(request.state, "auth_claims", None)
    if not claims or not claims.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can override risk levels")
    
    input_dto = OverrideRiskInput(
        passenger_id=passenger_id,
        new_risk_band=data.new_risk_band,
        reason=data.reason,
        actor_user_id=claims.user_id
    )
    await interactor.execute(input_dto)
    return {"status": "success", "message": "Risk level overridden successfully"}
