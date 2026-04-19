from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.risk.vo import DimensionType

class GetRiskConcentrationInteractor:
    def __init__(self, risk_repo: IRiskConcentrationRepository):
        self._risk_repo = risk_repo

    async def execute(self, dimension_type: str):
        try:
            dtype = DimensionType(dimension_type.lower())
        except ValueError:
            raise ValueError(f"Invalid dimension type: {dimension_type}. Supported: CHANNEL, AGGREGATOR, TERMINAL, CASHDESK")

        concentrations = await self._risk_repo.get_all_by_dimension(dtype)
        
        from app.presentation.api.dashboard.schemas import RiskConcentrationItem, RiskConcentrationResponse
        
        items = [
            RiskConcentrationItem(
                dimension_value=c.dimension_value,
                total_ops=c.total_ops,
                highrisk_ops=c.highrisk_ops,
                share_highrisk_ops=round(c.share_highrisk_ops, 2),
                lift_vs_base=round(c.lift_vs_base, 2)
            )
            for c in concentrations
        ]
        
        return RiskConcentrationResponse(dimension_type=dtype.value, items=items)
