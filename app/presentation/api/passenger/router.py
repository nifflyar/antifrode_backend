from fastapi import APIRouter, Request, HTTPException, status, Query
from dishka.integrations.fastapi import FromDishka, inject
import logging

from app.application.passenger.list_passengers import (
    ListPassengersInteractor,
    ListPassengersInputDTO,
    ListPassengersOutputDTO,
)
from app.application.passenger.get_passenger import (
    GetPassengerInteractor,
    GetPassengerInputDTO,
    GetPassengerOutputDTO,
)
from app.application.passenger.get_passenger_operations import (
    GetPassengerOperationsInteractor,
    GetPassengerOperationsInputDTO,
    GetPassengerOperationsOutputDTO,
)
from app.infrastructure.config import Config
from app.presentation.api.passenger.schemas import (
    PassengerListResponseSchema,
    PassengerProfileResponseSchema,
    PassengerOperationsResponseSchema,
)
from app.presentation.api.security import get_optional_auth_claims_from_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/passengers", tags=["passengers"])


@router.get("", response_model=PassengerListResponseSchema)
@inject
async def list_passengers(
    request: Request,
    config: FromDishka[Config],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    channel: str | None = Query(None),
    cashdesk: str | None = Query(None),
    terminal: str | None = Query(None),
    risk_band: str | None = Query(None),
    interactor: FromDishka[ListPassengersInteractor] = None,
) -> PassengerListResponseSchema:
    """List passengers with filters and pagination."""
    # Optional: add auth check if needed
    # claims = get_optional_auth_claims_from_request(request, config)

    result = await interactor(
        ListPassengersInputDTO(
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            channel=channel,
            cashdesk=cashdesk,
            terminal=terminal,
            risk_band=risk_band,
        )
    )

    return PassengerListResponseSchema(
        passengers=result.passengers,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get("/{passenger_id}", response_model=PassengerProfileResponseSchema)
@inject
async def get_passenger(
    passenger_id: int,
    request: Request,
    config: FromDishka[Config],
    interactor: FromDishka[GetPassengerInteractor] = None,
) -> PassengerProfileResponseSchema:
    """Get passenger profile by ID."""
    # Optional: add auth check if needed
    # claims = get_optional_auth_claims_from_request(request, config)

    try:
        result = await interactor(GetPassengerInputDTO(passenger_id=passenger_id))
        return PassengerProfileResponseSchema(
            passenger_id=result.passenger_id,
            fio_clean=result.fio_clean,
            fake_fio_score=result.fake_fio_score,
            first_seen_at=result.first_seen_at,
            last_seen_at=result.last_seen_at,
            score=result.score,
            features=result.features,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passenger {passenger_id} not found",
        )
    except Exception as e:
        logger.error(f"Error getting passenger {passenger_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/{passenger_id}/operations", response_model=PassengerOperationsResponseSchema)
@inject
async def get_passenger_operations(
    passenger_id: int,
    request: Request,
    config: FromDishka[Config],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    interactor: FromDishka[GetPassengerOperationsInteractor] = None,
) -> PassengerOperationsResponseSchema:
    """Get passenger operations (transactions)."""
    # Optional: add auth check if needed
    # claims = get_optional_auth_claims_from_request(request, config)

    try:
        result = await interactor(
            GetPassengerOperationsInputDTO(
                passenger_id=passenger_id,
                limit=limit,
                offset=offset,
            )
        )
        return PassengerOperationsResponseSchema(
            passenger_id=result.passenger_id,
            operations=result.operations,
            limit=result.limit,
            offset=result.offset,
        )
    except Exception as e:
        logger.error(f"Error getting operations for passenger {passenger_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


passenger_router = router
