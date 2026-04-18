from fastapi import APIRouter, Query, Depends, Request, HTTPException
from dishka.integrations.fastapi import FromDishka, inject
from datetime import datetime
from typing import Optional

from app.application.operations.list_suspicious import ListSuspiciousOperationsInteractor, ListSuspiciousOperationsInput
from app.presentation.api.operations.schemas import SuspiciousOperationsResponse, SuspiciousOperationSchema

operations_router = APIRouter(prefix="/operations", tags=["Operations"])

@operations_router.get("/suspicious", response_model=SuspiciousOperationsResponse)
@inject
async def get_suspicious_operations(
    request: Request,
    interactor: FromDishka[ListSuspiciousOperationsInteractor],
    train_no: Optional[str] = Query(None),
    cashdesk: Optional[str] = Query(None),
    terminal: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    claims = getattr(request.state, "auth_claims", None)
    if not claims:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    input_dto = ListSuspiciousOperationsInput(
        train_no=train_no,
        cashdesk=cashdesk,
        terminal=terminal,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )
    results, total = await interactor.execute(input_dto)
    
    return SuspiciousOperationsResponse(
        items=[
            SuspiciousOperationSchema(
                id=str(tx.id.value),
                passenger_id=str(tx.passenger_id.value),
                op_type=tx.op_type.value,
                op_datetime=tx.op_datetime,
                train_no=tx.train_no,
                amount=tx.amount,
                channel=tx.channel,
                terminal=tx.terminal,
                cashdesk=tx.cashdesk,
                risk_band=risk_band
            )
            for tx, risk_band in results
        ],
        total=total,
        limit=limit,
        offset=offset
    )
