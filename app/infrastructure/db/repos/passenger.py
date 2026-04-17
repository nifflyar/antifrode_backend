from sqlalchemy import func, select, update, cast, String

from app.domain.passenger.entity import Passenger
from app.domain.passenger.repository import IPassengerRepository
from app.domain.passenger.vo import PassengerId, RiskBand
from app.infrastructure.db.mappers.passenger import PassengerMapper, PassengerScoreMapper
from app.infrastructure.db.models.passenger import PassengerModel
from app.infrastructure.db.models.passenger_scores import PassengerScoreModel
from app.infrastructure.db.repos.base import BaseSQLAlchemyRepo


class PassengerRepositoryImpl(IPassengerRepository, BaseSQLAlchemyRepo):

    async def get_by_id(self, passenger_id: PassengerId) -> Passenger | None:
        stmt = select(PassengerModel).where(PassengerModel.id == passenger_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        passenger = PassengerMapper.to_domain(model)
        await self._load_score(passenger)
        return passenger

    async def get_all(
        self,
        risk_band: RiskBand | None = None,
        channel: str | None = None,
        cashdesk: str | None = None,
        terminal: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        seat_blocking_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Passenger]:
        stmt = select(PassengerModel)

        # Если нужна фильтрация по risk_band или seat_blocking — JOIN с passenger_scores
        needs_score_join = risk_band is not None or seat_blocking_only
        if needs_score_join:
            stmt = stmt.join(
                PassengerScoreModel,
                PassengerModel.id == PassengerScoreModel.passenger_id,
                isouter=False,
            )
            if risk_band is not None:
                stmt = stmt.where(PassengerScoreModel.risk_band == risk_band.value)
            if seat_blocking_only:
                stmt = stmt.where(PassengerScoreModel.seat_blocking_flag.is_(True))

        if date_from:
            stmt = stmt.where(PassengerModel.last_seen_at >= date_from)
        if date_to:
            stmt = stmt.where(PassengerModel.last_seen_at <= date_to)

        stmt = stmt.order_by(PassengerModel.last_seen_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        passengers = [PassengerMapper.to_domain(m) for m in result.scalars().all()]

        # Подгружаем скоры одним запросом
        await self._load_scores_bulk(passengers)
        return passengers

    async def count(self, risk_band: RiskBand | None = None) -> int:
        if risk_band is None:
            stmt = select(func.count(PassengerModel.id))
        else:
            stmt = (
                select(func.count(PassengerModel.id))
                .join(PassengerScoreModel, PassengerModel.id == PassengerScoreModel.passenger_id)
                .where(cast(PassengerScoreModel.risk_band, String) == risk_band.value)
            )
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def create_passenger(self, passenger: Passenger) -> None:
        model = PassengerMapper.to_model(passenger)
        self._session.add(model)
        await self._session.flush()

    async def update_passenger(self, passenger: Passenger) -> None:
        stmt = (
            update(PassengerModel)
            .where(PassengerModel.id == passenger.id)
            .values(
                fio_clean=passenger.fio_clean,
                fake_fio_score=passenger.fake_fio_score,
                last_seen_at=passenger.last_seen_at,
            )
        )
        await self._session.execute(stmt)

    async def delete_passenger(self, passenger_id: PassengerId) -> None:
        from sqlalchemy import delete
        stmt = delete(PassengerModel).where(PassengerModel.id == passenger_id)
        await self._session.execute(stmt)

    # ── helpers ──────────────────────────────────────────────────────────────

    async def _load_score(self, passenger: Passenger) -> None:
        stmt = select(PassengerScoreModel).where(
            PassengerScoreModel.passenger_id == passenger.id
        )
        result = await self._session.execute(stmt)
        score_model = result.scalar_one_or_none()
        if score_model:
            passenger.score = PassengerScoreMapper.to_domain(score_model)

    async def _load_scores_bulk(self, passengers: list[Passenger]) -> None:
        if not passengers:
            return
        ids = [p.id.value for p in passengers]
        stmt = select(PassengerScoreModel).where(
            PassengerScoreModel.passenger_id.in_(ids)
        )
        result = await self._session.execute(stmt)
        score_map = {m.passenger_id.value: m for m in result.scalars().all()}
        for passenger in passengers:
            score_model = score_map.get(passenger.id.value)
            if score_model:
                passenger.score = PassengerScoreMapper.to_domain(score_model)
