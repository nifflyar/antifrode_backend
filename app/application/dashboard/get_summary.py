from dataclasses import dataclass
from app.application.common.interactor import Interactor
from app.domain.passenger.repository import IPassengerRepository
from app.domain.passenger.vo import RiskBand
from app.domain.transaction.repository import ITransactionRepository
from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.risk.vo import DimensionType


@dataclass
class GetDashboardSummaryInputDTO:
    pass


@dataclass
class GetDashboardSummaryOutputDTO:
    total_passengers: int
    high_risk_count: int
    critical_risk_count: int
    share_suspicious_ops: float
    top_risk_channel: str | None
    top_risk_terminal: str | None


class GetDashboardSummaryInteractor(Interactor[GetDashboardSummaryInputDTO, GetDashboardSummaryOutputDTO]):
    def __init__(
        self,
        passenger_repository: IPassengerRepository,
        transaction_repository: ITransactionRepository,
        risk_concentration_repository: IRiskConcentrationRepository,
    ) -> None:
        self.passenger_repository = passenger_repository
        self.transaction_repository = transaction_repository
        self.risk_concentration_repository = risk_concentration_repository

    async def __call__(self, data: GetDashboardSummaryInputDTO) -> GetDashboardSummaryOutputDTO:
        # Get passenger counts
        total_passengers = await self.passenger_repository.count()
        high_risk_count = await self.passenger_repository.count(risk_band=RiskBand.HIGH)
        critical_risk_count = await self.passenger_repository.count(risk_band=RiskBand.CRITICAL)

        # Calculate share of suspicious ops
        total_ops = await self.transaction_repository.count_all()
        suspicious_ops = await self.transaction_repository.count_suspicious()
        share_suspicious_ops = (suspicious_ops / total_ops * 100) if total_ops > 0 else 0.0

        # Get top risk channel
        top_channel = await self.risk_concentration_repository.get_top_dimension(
            DimensionType.CHANNEL.value, top_n=1
        )
        top_risk_channel = top_channel.dimension_value if top_channel else None

        # Get top risk terminal
        top_terminal = await self.risk_concentration_repository.get_top_dimension(
            DimensionType.TERMINAL.value, top_n=1
        )
        top_risk_terminal = top_terminal.dimension_value if top_terminal else None

        return GetDashboardSummaryOutputDTO(
            total_passengers=total_passengers,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            share_suspicious_ops=round(share_suspicious_ops, 2),
            top_risk_channel=top_risk_channel,
            top_risk_terminal=top_risk_terminal,
        )
