from dataclasses import dataclass
from datetime import datetime
from app.application.common.interactor import Interactor
from app.domain.transaction.repository import ITransactionRepository


@dataclass
class GetRiskTrendInputDTO:
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass
class RiskTrendItem:
    date: str
    total_ops: int
    highrisk_ops: int
    share: float


@dataclass
class GetRiskTrendOutputDTO:
    trends: list[RiskTrendItem]


class GetRiskTrendInteractor(Interactor[GetRiskTrendInputDTO, GetRiskTrendOutputDTO]):
    def __init__(
        self,
        transaction_repository: ITransactionRepository,
    ) -> None:
        self.transaction_repository = transaction_repository

    async def __call__(self, data: GetRiskTrendInputDTO) -> GetRiskTrendOutputDTO:
        daily_stats = await self.transaction_repository.get_daily_stats(
            date_from=data.date_from,
            date_to=data.date_to,
        )

        trends = [
            RiskTrendItem(
                date=stat["date"],
                total_ops=stat["total_ops"],
                highrisk_ops=stat["highrisk_ops"],
                share=round(
                    (stat["highrisk_ops"] / stat["total_ops"] * 100)
                    if stat["total_ops"] > 0
                    else 0.0,
                    2,
                ),
            )
            for stat in daily_stats
        ]

        return GetRiskTrendOutputDTO(trends=trends)
