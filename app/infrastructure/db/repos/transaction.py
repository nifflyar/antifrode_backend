from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.domain.passenger.vo import PassengerId, RiskBand
from app.domain.transaction.entity import Transaction
from app.domain.transaction.repository import ITransactionRepository
from app.domain.transaction.vo import TransactionId
from app.domain.upload.vo import UploadId
from app.infrastructure.db.mappers.transaction import TransactionMapper
from app.infrastructure.db.models.passenger_scores import PassengerScoreModel
from app.infrastructure.db.models.transaction import TransactionModel
from app.infrastructure.db.repos.base import BaseSQLAlchemyRepo

_SUSPICIOUS_BANDS = (RiskBand.high.value, RiskBand.critical.value)


class TransactionRepositoryImpl(ITransactionRepository, BaseSQLAlchemyRepo):

    async def get_by_id(self, transaction_id: TransactionId) -> Transaction | None:
        stmt = select(TransactionModel).where(TransactionModel.id == transaction_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return TransactionMapper.to_domain(model) if model else None

    async def get_all_by_upload_id(
        self, upload_id: UploadId, limit: int = 500, offset: int = 0
    ) -> list[Transaction]:
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.upload_id == upload_id)
            .order_by(TransactionModel.op_datetime.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [TransactionMapper.to_domain(m) for m in result.scalars().all()]

    async def get_by_passenger_id(
        self, passenger_id: PassengerId, limit: int = 100, offset: int = 0
    ) -> list[Transaction]:
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.passenger_id == passenger_id)
            .order_by(TransactionModel.op_datetime.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [TransactionMapper.to_domain(m) for m in result.scalars().all()]

    async def get_suspicious(
        self,
        train_no: str | None = None,
        cashdesk: str | None = None,
        terminal: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Transaction, RiskBand]]:
        stmt = (
            select(TransactionModel, PassengerScoreModel.risk_band)
            .join(
                PassengerScoreModel,
                TransactionModel.passenger_id == PassengerScoreModel.passenger_id,
            )
            .where(PassengerScoreModel.risk_band.in_(_SUSPICIOUS_BANDS))
        )
        stmt = self._apply_filters(stmt, train_no, cashdesk, terminal, date_from, date_to)
        stmt = stmt.order_by(TransactionModel.op_datetime.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [
            (TransactionMapper.to_domain(row[0]), RiskBand(row[1]))
            for row in result.all()
        ]

    async def count_suspicious(
        self,
        train_no: str | None = None,
        cashdesk: str | None = None,
        terminal: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = (
            select(func.count(TransactionModel.id))
            .join(
                PassengerScoreModel,
                TransactionModel.passenger_id == PassengerScoreModel.passenger_id,
            )
            .where(PassengerScoreModel.risk_band.in_(_SUSPICIOUS_BANDS))
        )
        stmt = self._apply_filters(stmt, train_no, cashdesk, terminal, date_from, date_to)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def count_all(self) -> int:
        stmt = select(func.count(TransactionModel.id))
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def create_batch(self, transactions: list[Transaction]) -> None:
        """Bulk insert через PostgreSQL INSERT ... ON CONFLICT DO NOTHING."""
        if not transactions:
            return
        rows = [
            {
                "id": tx.id.value,
                "upload_id": tx.upload_id.value,
                "source": tx.source,
                "op_type": tx.op_type.value,
                "op_datetime": tx.op_datetime,
                "dep_datetime": tx.dep_datetime,
                "train_no": tx.train_no,
                "channel": tx.channel,
                "aggregator": tx.aggregator,
                "terminal": tx.terminal,
                "cashdesk": tx.cashdesk,
                "point_of_sale": tx.point_of_sale,
                "amount": tx.amount,
                "fee": tx.fee,
                "fio": tx.fio,
                "iin": tx.iin,
                "phone": tx.phone,
                "doc_no": tx.doc_no,
                "order_no": tx.order_no,
                "dep_station": tx.dep_station,
                "arr_station": tx.arr_station,
                "route": tx.route,
                "tariff_type": tx.tariff_type,
                "service_class": tx.service_class,
                "gender": tx.gender,
                "branch": tx.branch,
                "carrier": tx.carrier,
                "settlement_type": tx.settlement_type,
                "passenger_id": tx.passenger_id.value if tx.passenger_id else None,
            }
            for tx in transactions
        ]
        stmt = insert(TransactionModel).on_conflict_do_nothing(index_elements=["id"])
        await self._session.execute(stmt, rows)

    async def get_risk_trend(
        self, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> list[dict]:
        """Возвращает статистику по дням: дата, общее кол-во, подозрительные."""
        # Субзапрос для подсчета подозрительных транзакций
        suspicious_sub = (
            select(
                func.date_trunc("day", TransactionModel.op_datetime).label("day"),
                func.count(TransactionModel.id).label("suspicious_count"),
            )
            .join(
                PassengerScoreModel,
                TransactionModel.passenger_id == PassengerScoreModel.passenger_id,
            )
            .where(PassengerScoreModel.risk_band.in_(_SUSPICIOUS_BANDS))
            .group_by("day")
            .subquery()
        )

        # Основной запрос для общего кол-ва
        day_expr = func.date_trunc("day", TransactionModel.op_datetime)
        stmt = (
            select(
                day_expr.label("day"),
                func.count(TransactionModel.id).label("total_count"),
                func.coalesce(suspicious_sub.c.suspicious_count, 0).label("suspicious_count"),
            )
            .outerjoin(suspicious_sub, day_expr == suspicious_sub.c.day)
        )

        if date_from:
            stmt = stmt.where(TransactionModel.op_datetime >= date_from)
        if date_to:
            stmt = stmt.where(TransactionModel.op_datetime <= date_to)

        stmt = stmt.group_by(day_expr, suspicious_sub.c.suspicious_count).order_by(day_expr)
        
        result = await self._session.execute(stmt)
        return [
            {
                "date": row.day,
                "total_count": row.total_count,
                "suspicious_count": row.suspicious_count,
            }
            for row in result.all()
        ]

    async def get_dimension_stats(self, dimension_column: str) -> list[dict]:
        """Группирует транзакции по колонке (channel, terminal и т.д.) 
        и считает кол-во всего / подозрительных."""
        col = getattr(TransactionModel, dimension_column, None)
        if col is None:
            raise ValueError(f"Invalid dimension column: {dimension_column}")

        # Субзапрос для подозрительных
        susp_sub = (
            select(
                col.label("dim"),
                func.count(TransactionModel.id).label("suspicious_count"),
            )
            .join(PassengerScoreModel, TransactionModel.passenger_id == PassengerScoreModel.passenger_id)
            .where(PassengerScoreModel.risk_band.in_(_SUSPICIOUS_BANDS))
            .group_by("dim")
            .subquery()
        )

        # Основной запрос
        stmt = (
            select(
                col.label("dim"),
                func.count(TransactionModel.id).label("total_count"),
                func.coalesce(susp_sub.c.suspicious_count, 0).label("suspicious_count")
            )
            .outerjoin(susp_sub, col == susp_sub.c.dim)
            .group_by(col, susp_sub.c.suspicious_count)
            .order_by(func.count(TransactionModel.id).desc())
        )

        result = await self._session.execute(stmt)
        return [
            {
                "value": row.dim,
                "total_count": row.total_count,
                "suspicious_count": row.suspicious_count
            }
            # row.dim может быть None для некоторых транзакций, фильтруем или оставляем как 'Unknown'
            for row in result.all() if row.dim is not None
        ]

    #  helpers 

    @staticmethod
    def _apply_filters(stmt, train_no, cashdesk, terminal, date_from, date_to):
        if train_no:
            stmt = stmt.where(TransactionModel.train_no == train_no)
        if cashdesk:
            stmt = stmt.where(TransactionModel.cashdesk == cashdesk)
        if terminal:
            stmt = stmt.where(TransactionModel.terminal == terminal)
        if date_from:
            stmt = stmt.where(TransactionModel.op_datetime >= date_from)
        if date_to:
            stmt = stmt.where(TransactionModel.op_datetime <= date_to)
        return stmt
