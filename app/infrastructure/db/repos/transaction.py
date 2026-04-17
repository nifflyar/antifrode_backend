from datetime import datetime

from sqlalchemy import func, select, cast, String, case
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

_SUSPICIOUS_BANDS = (RiskBand.HIGH.value, RiskBand.CRITICAL.value)


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
    ) -> list[Transaction]:
        stmt = (
            select(TransactionModel)
            .join(
                PassengerScoreModel,
                TransactionModel.passenger_id == PassengerScoreModel.passenger_id,
            )
            .where(cast(PassengerScoreModel.risk_band, String).in_(_SUSPICIOUS_BANDS))
        )
        stmt = self._apply_filters(stmt, train_no, cashdesk, terminal, date_from, date_to)
        stmt = stmt.order_by(TransactionModel.op_datetime.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [TransactionMapper.to_domain(m) for m in result.scalars().all()]

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
            .where(cast(PassengerScoreModel.risk_band, String).in_(_SUSPICIOUS_BANDS))
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
                "op_type": tx.op_type.value if hasattr(tx.op_type, 'value') else str(tx.op_type).lower(),
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
                "doc_no": tx.doc_no,
                "passenger_id": tx.passenger_id.value if tx.passenger_id else None,
            }
            for tx in transactions
        ]
        stmt = insert(TransactionModel).on_conflict_do_nothing(index_elements=["id"])
        await self._session.execute(stmt, rows)

    async def get_daily_stats(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        """Get daily aggregated stats: date, total_ops, highrisk_ops."""
        from sqlalchemy import Date

        stmt = (
            select(
                cast(TransactionModel.op_datetime, Date).label("date"),
                func.count(TransactionModel.id).label("total_ops"),
                func.sum(
                    case(
                        (cast(PassengerScoreModel.risk_band, String).in_(_SUSPICIOUS_BANDS), 1),
                        else_=0,
                    )
                ).label("highrisk_ops"),
            )
            .outerjoin(
                PassengerScoreModel,
                TransactionModel.passenger_id == PassengerScoreModel.passenger_id,
            )
        )

        if date_from:
            stmt = stmt.where(TransactionModel.op_datetime >= date_from)
        if date_to:
            stmt = stmt.where(TransactionModel.op_datetime <= date_to)

        stmt = stmt.group_by(cast(TransactionModel.op_datetime, Date)).order_by(
            "date"
        )

        result = await self._session.execute(stmt)
        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "total_ops": row.total_ops or 0,
                "highrisk_ops": row.highrisk_ops or 0,
            }
            for row in result.all()
        ]

    # ── helpers ──────────────────────────────────────────────────────────────

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
