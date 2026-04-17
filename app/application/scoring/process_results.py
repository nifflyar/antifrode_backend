import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from uuid import uuid4

from app.application.common.interactor import Interactor
from app.application.common.transaction import TransactionManager
from app.domain.passenger.entity import PassengerScore
from app.domain.passenger.vo import PassengerId, RiskBand
from app.domain.passenger.score_repository import IPassengerScoreRepository
from app.domain.risk.entity import RiskConcentration
from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.risk.vo import DimensionType
from app.infrastructure.ml_client import MLScoringResult, MLScoringItem

logger = logging.getLogger(__name__)


@dataclass
class ProcessScoringResultsInputDTO:
    """Input for scoring results processing."""
    ml_result: MLScoringResult


@dataclass
class ProcessScoringResultsOutputDTO:
    """Output from scoring results processing."""
    processed_passengers: int
    updated_risk_concentrations: int


class ProcessScoringResultsInteractor(Interactor[ProcessScoringResultsInputDTO, ProcessScoringResultsOutputDTO]):
    """
    Process ML scoring results.

    1. Updates PassengerScore for each passenger with ML scores
    2. Recalculates RiskConcentration by dimension_type
    3. Performs bulk upserts
    """

    def __init__(
        self,
        passenger_score_repository: IPassengerScoreRepository,
        risk_concentration_repository: IRiskConcentrationRepository,
        transaction_manager: TransactionManager,
    ):
        self.passenger_score_repository = passenger_score_repository
        self.risk_concentration_repository = risk_concentration_repository
        self.transaction_manager = transaction_manager

    async def __call__(
        self, data: ProcessScoringResultsInputDTO
    ) -> ProcessScoringResultsOutputDTO:
        """Process ML scoring results and update repositories."""

        # Convert ML results to PassengerScore entities
        score_items = self._build_passenger_scores(data.ml_result.results)

        # Bulk upsert passenger scores
        await self.passenger_score_repository.bulk_upsert(score_items)
        logger.info(f"Upserted {len(score_items)} passenger scores")

        # Recalculate risk concentrations for all dimension types
        risk_concentrations = await self._recalculate_risk_concentrations()
        await self.risk_concentration_repository.save_batch(risk_concentrations)
        logger.info(f"Updated {len(risk_concentrations)} risk concentration records")

        # Commit transaction
        await self.transaction_manager.commit()

        return ProcessScoringResultsOutputDTO(
            processed_passengers=len(score_items),
            updated_risk_concentrations=len(risk_concentrations),
        )

    def _build_passenger_scores(
        self, ml_items: list[MLScoringItem]
    ) -> list[tuple[PassengerId, PassengerScore]]:
        """Convert ML scoring items to (PassengerId, PassengerScore) tuples."""
        scores = []

        for item in ml_items:
            passenger_id = PassengerId(item.passenger_id)
            risk_band = self._parse_risk_band(item.risk_band)

            score = PassengerScore(
                ml_score=item.ml_score,
                final_score=item.ml_score,  # or combine with rule_score if available
                risk_band=risk_band,
                top_reasons=item.top_reasons,
                scored_at=datetime.now(UTC),
            )

            scores.append((passenger_id, score))

        return scores

    def _parse_risk_band(self, risk_band_str: str) -> RiskBand:
        """Parse risk band string to RiskBand enum."""
        try:
            # Convert to lowercase first to match enum values
            normalized = risk_band_str.lower()
            return RiskBand(normalized)
        except (ValueError, KeyError):
            logger.warning(f"Unknown risk band '{risk_band_str}', defaulting to LOW")
            return RiskBand.LOW

    async def _recalculate_risk_concentrations(self) -> list[RiskConcentration]:
        """
        Recalculate risk concentrations across all dimensions.

        For each dimension type, calculate high-risk concentration.
        """
        risk_concentrations = []

        # Get total high-risk count across all passengers
        total_high_risk = await self.passenger_score_repository.count_by_risk_band(
            RiskBand.HIGH
        ) + await self.passenger_score_repository.count_by_risk_band(RiskBand.CRITICAL)

        base_share = total_high_risk / (
            total_high_risk + 1
        )  # Prevent division by zero; approximate base

        for dimension_type in DimensionType:
            # In a real scenario, you'd query passengers grouped by this dimension
            # For now, create placeholder concentrations
            # This would require additional repository methods or aggregation

            # Placeholder: Create one record per dimension type
            concentration = RiskConcentration.create(
                concentration_id=f"{str(uuid4())[:8]}",
                dimension_type=dimension_type,
                dimension_value="aggregated",
                total_ops=total_high_risk,
                highrisk_ops=total_high_risk,
                base_share=base_share,
            )
            risk_concentrations.append(concentration)

        return risk_concentrations
