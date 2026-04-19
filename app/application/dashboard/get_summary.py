from app.domain.passenger.repository import IPassengerRepository
from app.domain.passenger.vo import RiskBand
from app.domain.transaction.repository import ITransactionRepository
from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.risk.vo import DimensionType

class GetDashboardSummaryInteractor:
    def __init__(
        self,
        passenger_repo: IPassengerRepository,
        transaction_repo: ITransactionRepository,
        risk_repo: IRiskConcentrationRepository,
    ):
        self._passenger_repo = passenger_repo
        self._transaction_repo = transaction_repo
        self._risk_repo = risk_repo

    async def execute(self):
        # 1. Посажиры по рискам
        total_passengers = await self._passenger_repo.count()
        high_risk_count = await self._passenger_repo.count(RiskBand.high)
        critical_risk_count = await self._passenger_repo.count(RiskBand.critical)

        # 2. Транзакции
        total_ops = await self._transaction_repo.count_all()
        suspicious_ops = await self._transaction_repo.count_suspicious()
        
        share_suspicious = (suspicious_ops / total_ops * 100) if total_ops > 0 else 0.0

        # 3. Топ риски
        top_channel = await self._risk_repo.get_top_dimension("CHANNEL")
        top_terminal = await self._risk_repo.get_top_dimension("TERMINAL")

        from app.presentation.api.dashboard.schemas import DashboardSummaryResponse
        return DashboardSummaryResponse(
            total_passengers=total_passengers,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            share_suspicious_ops=round(share_suspicious, 2),
            top_risk_channel=top_channel.dimension_value if top_channel else None,
            top_risk_terminal=top_terminal.dimension_value if top_terminal else None,
        )
