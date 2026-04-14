from datetime import datetime

from sqlalchemy import TIMESTAMP, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.passenger.vo import PassengerId
from app.domain.passenger.entity import PassengerFeatures, PassengerScore

from .base import BaseORMModel
from .types.entities import (
    PassengerIdType,
    PassengerFeaturesType,
    PassengerScoreType,
)


class PassengerModel(BaseORMModel):
    __tablename__ = "passengers"

    id: Mapped[PassengerId] = mapped_column(PassengerIdType, primary_key=True)
    fio_clean: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    fake_fio_score: Mapped[float] = mapped_column(Float, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    features: Mapped[PassengerFeatures | None] = mapped_column(
        PassengerFeaturesType, nullable=True
    )
    score: Mapped[PassengerScore | None] = mapped_column(
        PassengerScoreType, nullable=True
    )
