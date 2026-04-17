from dataclasses import dataclass

from app.application.common.interactor import Interactor
from app.domain.passenger.repository import IPassengerRepository
from app.domain.passenger.vo import RiskBand
from app.domain.transaction.repository import ITransactionRepository


@dataclass
class ListPassengersInputDTO:
    limit: int = 20
    offset: int = 0
    date_from: str | None = None
    date_to: str | None = None
    channel: str | None = None
    cashdesk: str | None = None
    terminal: str | None = None
    risk_band: str | None = None


@dataclass
class PassengerListItemDTO:
    passenger_id: int
    final_score: float
    risk_band: str
    top_reasons: list[str]
    refund_cnt: int
    max_tickets_month: int
    seat_blocking_flag: bool


@dataclass
class ListPassengersOutputDTO:
    passengers: list[PassengerListItemDTO]
    total: int
    limit: int
    offset: int


class ListPassengersInteractor(Interactor[ListPassengersInputDTO, ListPassengersOutputDTO]):
    def __init__(
        self,
        passenger_repository: IPassengerRepository,
        transaction_repository: ITransactionRepository,
    ) -> None:
        self.passenger_repository = passenger_repository
        self.transaction_repository = transaction_repository

    async def __call__(self, data: ListPassengersInputDTO) -> ListPassengersOutputDTO:
        # Validate limits
        if data.limit > 100:
            data.limit = 100
        if data.limit < 1:
            data.limit = 1

        # Parse risk_band if provided
        risk_band = None
        if data.risk_band:
            try:
                risk_band = RiskBand(data.risk_band)
            except ValueError:
                risk_band = None

        # Fetch passengers
        passengers = await self.passenger_repository.get_all(
            risk_band=risk_band,
            channel=data.channel,
            cashdesk=data.cashdesk,
            terminal=data.terminal,
            date_from=data.date_from,
            date_to=data.date_to,
            limit=data.limit,
            offset=data.offset,
        )

        # Get total count
        total = await self.passenger_repository.count(risk_band=risk_band)

        # Convert to output DTOs
        output_passengers = [
            PassengerListItemDTO(
                passenger_id=p.id.value,
                final_score=p.score.final_score if p.score else 0.0,
                risk_band=p.score.risk_band.value if p.score else "low",
                top_reasons=p.score.top_reasons if p.score else [],
                refund_cnt=p.features.refund_cnt if p.features else 0,
                max_tickets_month=p.features.max_tickets_month if p.features else 0,
                seat_blocking_flag=p.score.seat_blocking_flag if p.score else False,
            )
            for p in passengers
        ]

        return ListPassengersOutputDTO(
            passengers=output_passengers,
            total=total,
            limit=data.limit,
            offset=data.offset,
        )
