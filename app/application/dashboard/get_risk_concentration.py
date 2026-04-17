from dataclasses import dataclass
from app.application.common.interactor import Interactor
from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.risk.vo import DimensionType


@dataclass
class GetRiskConcentrationInputDTO:
    dimension_type: str


@dataclass
class RiskConcentrationItem:
    dimension_value: str
    total_ops: int
    highrisk_ops: int
    share_highrisk_ops: float
    lift_vs_base: float


@dataclass
class GetRiskConcentrationOutputDTO:
    items: list[RiskConcentrationItem]


class GetRiskConcentrationInteractor(Interactor[GetRiskConcentrationInputDTO, GetRiskConcentrationOutputDTO]):
    def __init__(
        self,
        risk_concentration_repository: IRiskConcentrationRepository,
    ) -> None:
        self.risk_concentration_repository = risk_concentration_repository

    async def __call__(self, data: GetRiskConcentrationInputDTO) -> GetRiskConcentrationOutputDTO:
        # Validate dimension type
        try:
            dimension_type = DimensionType(data.dimension_type)
        except ValueError:
            valid_types = ", ".join([dt.value for dt in DimensionType])
            raise ValueError(f"Invalid dimension_type. Valid values: {valid_types}")

        concentrations = await self.risk_concentration_repository.get_all_by_dimension(
            dimension_type=dimension_type
        )

        items = [
            RiskConcentrationItem(
                dimension_value=conc.dimension_value,
                total_ops=conc.total_ops,
                highrisk_ops=conc.highrisk_ops,
                share_highrisk_ops=round(conc.share_highrisk_ops * 100, 2),
                lift_vs_base=round(conc.lift_vs_base, 2),
            )
            for conc in concentrations
        ]

        return GetRiskConcentrationOutputDTO(items=items)
