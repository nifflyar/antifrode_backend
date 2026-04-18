from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

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
        await self._load_features(passenger)
        return passenger

    async def get_all(
        self,
        risk_band: RiskBand | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Passenger]:
        stmt = select(PassengerModel)

        if search:
            s = f"%{search}%"
            # Try to convert search to int for ID search
            try:
                search_int = int(search)
                stmt = stmt.where(
                    (PassengerModel.fio_clean.ilike(s)) | (PassengerModel.id == search_int)
                )
            except (ValueError, TypeError):
                # If not a number, just search by name
                stmt = stmt.where(PassengerModel.fio_clean.ilike(s))

        if risk_band is not None:
            stmt = stmt.join(
                PassengerScoreModel,
                PassengerModel.id == PassengerScoreModel.passenger_id,
            ).where(PassengerScoreModel.risk_band == risk_band.value)

        stmt = stmt.order_by(PassengerModel.last_seen_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        passengers = [PassengerMapper.to_domain(m) for m in result.scalars().all()]

        # Подгружаем скоры и фичи одним запросом
        await self._load_scores_bulk(passengers)
        await self._load_features_bulk(passengers)
        return passengers

    async def count(self, risk_band: RiskBand | None = None, search: str | None = None) -> int:
        stmt = select(func.count(PassengerModel.id))

        if search:
            s = f"%{search}%"
            # Try to convert search to int for ID search
            try:
                search_int = int(search)
                stmt = stmt.where(
                    (PassengerModel.fio_clean.ilike(s)) | (PassengerModel.id == search_int)
                )
            except (ValueError, TypeError):
                # If not a number, just search by name
                stmt = stmt.where(PassengerModel.fio_clean.ilike(s))

        if risk_band is not None:
            stmt = stmt.join(
                PassengerScoreModel,
                PassengerModel.id == PassengerScoreModel.passenger_id,
            ).where(PassengerScoreModel.risk_band == risk_band.value)

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

    #  helpers 

    async def _load_score(self, passenger: Passenger) -> None:
        stmt = select(PassengerScoreModel).where(
            PassengerScoreModel.passenger_id == passenger.id
        )
        result = await self._session.execute(stmt)
        score_model = result.scalar_one_or_none()
        if score_model:
            passenger.score = PassengerScoreMapper.to_domain(score_model)

    async def _load_features(self, passenger: Passenger) -> None:
        from app.infrastructure.db.models.passenger_features import PassengerFeaturesModel
        from app.infrastructure.db.mappers.passenger import PassengerFeaturesMapper
        stmt = select(PassengerFeaturesModel).where(
            PassengerFeaturesModel.passenger_id == passenger.id
        )
        result = await self._session.execute(stmt)
        feature_model = result.scalar_one_or_none()
        if feature_model:
            passenger.features = PassengerFeaturesMapper.to_domain(feature_model)

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

    async def _load_features_bulk(self, passengers: list[Passenger]) -> None:
        if not passengers:
            return
        from app.infrastructure.db.models.passenger_features import PassengerFeaturesModel
        from app.infrastructure.db.mappers.passenger import PassengerFeaturesMapper
        ids = [p.id.value for p in passengers]
        stmt = select(PassengerFeaturesModel).where(
            PassengerFeaturesModel.passenger_id.in_(ids)
        )
        result = await self._session.execute(stmt)
        feature_map = {m.passenger_id.value: m for m in result.scalars().all()}
        for passenger in passengers:
            feature_model = feature_map.get(passenger.id.value)
            if feature_model:
                passenger.features = PassengerFeaturesMapper.to_domain(feature_model)
