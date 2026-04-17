from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.transaction.entity import Transaction
from app.domain.transaction.vo import TransactionId
from app.domain.upload.vo import UploadId
from app.domain.passenger.vo import PassengerId, RiskBand


class ITransactionRepository(ABC):

    @abstractmethod
    async def get_by_id(self, transaction_id: TransactionId) -> Transaction | None: ...

    @abstractmethod
    async def get_all_by_upload_id(
        self, upload_id: UploadId, limit: int = 500, offset: int = 0
    ) -> list[Transaction]: ...

    @abstractmethod
    async def get_by_passenger_id(
        self, passenger_id: PassengerId, limit: int = 100, offset: int = 0
    ) -> list[Transaction]: ...

    @abstractmethod
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
        """Транзакции пассажиров с risk_band IN (HIGH, CRITICAL)."""
        ...

    @abstractmethod
    async def count_suspicious(
        self,
        train_no: str | None = None,
        cashdesk: str | None = None,
        terminal: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int: ...

    @abstractmethod
    async def count_all(self) -> int: ...

    @abstractmethod
    async def create_batch(self, transactions: list[Transaction]) -> None:
        """Bulk insert транзакций — используется ETL-пайплайном."""
        ...

    @abstractmethod
    async def get_daily_stats(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        """Get daily aggregated stats: date, total_ops, highrisk_ops."""
        ...
