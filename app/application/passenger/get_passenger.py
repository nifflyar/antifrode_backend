from dataclasses import dataclass

from app.application.common.interactor import Interactor
from app.domain.passenger.repository import IPassengerRepository
from app.domain.passenger.vo import PassengerId


@dataclass
class GetPassengerInputDTO:
    passenger_id: int


@dataclass
class PassengerFeatureDTO:
    total_tickets: int
    refund_cnt: int
    refund_share: float
    night_tickets: int
    night_share: float
    max_tickets_month: int
    max_tickets_same_depday: int
    refund_close_ratio: float
    tickets_per_train_peak: float
    fio_fake_score_max: float


@dataclass
class PassengerScoreDTO:
    rule_score: float
    ml_score: float
    final_score: float
    risk_band: str
    top_reasons: list[str]
    seat_blocking_flag: bool


@dataclass
class GetPassengerOutputDTO:
    passenger_id: int
    fio_clean: str
    fake_fio_score: float
    first_seen_at: str
    last_seen_at: str
    score: PassengerScoreDTO | None
    features: PassengerFeatureDTO | None


class GetPassengerInteractor(Interactor[GetPassengerInputDTO, GetPassengerOutputDTO]):
    def __init__(self, passenger_repository: IPassengerRepository) -> None:
        self.passenger_repository = passenger_repository

    async def __call__(self, data: GetPassengerInputDTO) -> GetPassengerOutputDTO:
        passenger = await self.passenger_repository.get_by_id(PassengerId(data.passenger_id))

        if not passenger:
            raise ValueError(f"Passenger {data.passenger_id} not found")

        score_dto = None
        if passenger.score:
            score_dto = PassengerScoreDTO(
                rule_score=passenger.score.rule_score,
                ml_score=passenger.score.ml_score,
                final_score=passenger.score.final_score,
                risk_band=passenger.score.risk_band.value,
                top_reasons=passenger.score.top_reasons,
                seat_blocking_flag=passenger.score.seat_blocking_flag,
            )

        features_dto = None
        if passenger.features:
            features_dto = PassengerFeatureDTO(
                total_tickets=passenger.features.total_tickets,
                refund_cnt=passenger.features.refund_cnt,
                refund_share=passenger.features.refund_share,
                night_tickets=passenger.features.night_tickets,
                night_share=passenger.features.night_share,
                max_tickets_month=passenger.features.max_tickets_month,
                max_tickets_same_depday=passenger.features.max_tickets_same_depday,
                refund_close_ratio=passenger.features.refund_close_ratio,
                tickets_per_train_peak=passenger.features.tickets_per_train_peak,
                fio_fake_score_max=passenger.features.fio_fake_score_max,
            )

        return GetPassengerOutputDTO(
            passenger_id=passenger.id.value,
            fio_clean=passenger.fio_clean,
            fake_fio_score=passenger.fake_fio_score,
            first_seen_at=passenger.first_seen_at.isoformat(),
            last_seen_at=passenger.last_seen_at.isoformat(),
            score=score_dto,
            features=features_dto,
        )
