# app/domain/passenger/entity.py
from dataclasses import dataclass, field
from datetime import datetime
from app.domain.passenger.vo import PassengerId, RiskBand


@dataclass
class PassengerFeatures:

    total_tickets: int = 0
    refund_cnt: int = 0
    refund_share: float = 0.0
    night_tickets: int = 0
    night_share: float = 0.0
    max_tickets_month: int = 0
    max_tickets_same_depday: int = 0
    refund_close_ratio: float = 0.0
    tickets_per_train_peak: float = 0.0
    fio_fake_score_max: float = 0.0

    def refund_rate_is_high(self, threshold: float = 0.5) -> bool:
        return self.refund_share >= threshold

    def has_seat_blocking_pattern(
        self,
        min_tickets_same_day: int = 3,
        min_refund_close: float = 0.6,
    ) -> bool:
        return (
            self.max_tickets_same_depday >= min_tickets_same_day
            and self.refund_close_ratio >= min_refund_close
        )

@dataclass
class PassengerScore:
    rule_score: float = 0.0
    ml_score: float = 0.0
    final_score: float = 0.0
    risk_band: RiskBand = RiskBand.low
    top_reasons: list[str] = field(default_factory=list)
    seat_blocking_flag: bool = False
    is_manual: bool = False
    scored_at: datetime | None = None

    def is_critical(self) -> bool:
        return self.risk_band == RiskBand.critical

    def is_suspicious(self) -> bool:
        return self.risk_band.is_suspicious()


@dataclass
class Passenger:
    id: PassengerId
    fio_clean: str
    fake_fio_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    features: PassengerFeatures | None = None
    score: PassengerScore | None = None


    def is_scored(self) -> bool:
        return self.score is not None

    def is_high_risk(self) -> bool:
        return self.score is not None and self.score.is_suspicious()

    def has_seat_blocking(self) -> bool:
        return self.score is not None and self.score.seat_blocking_flag

    def likely_fake_identity(self, threshold: float = 0.7) -> bool:
        return self.fake_fio_score >= threshold

    def apply_score(self, score: PassengerScore) -> None:
        self.score = score

    def update_activity(self, seen_at: datetime) -> None:
        if seen_at > self.last_seen_at:
            self.last_seen_at = seen_at

    @classmethod
    def create(cls, passenger_id: int, fio_clean: str,
               first_seen_at: datetime,
               fake_fio_score: float = 0.0) -> "Passenger":
        return cls(
            id=PassengerId(passenger_id),
            fio_clean=fio_clean,
            fake_fio_score=fake_fio_score,
            first_seen_at=first_seen_at,
            last_seen_at=first_seen_at,
        )