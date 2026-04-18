from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.domain.transaction.entity import Transaction
from app.domain.transaction.repository import ITransactionRepository
from app.domain.passenger.vo import RiskBand

@dataclass
class ListSuspiciousOperationsInput:
    train_no: Optional[str] = None
    cashdesk: Optional[str] = None
    terminal: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 100
    offset: int = 0

class ListSuspiciousOperationsInteractor:
    def __init__(self, transaction_repo: ITransactionRepository):
        self._tx_repo = transaction_repo

    async def execute(self, input_dto: ListSuspiciousOperationsInput) -> tuple[list[tuple[Transaction, RiskBand]], int]:
        results = await self._tx_repo.get_suspicious(
            train_no=input_dto.train_no,
            cashdesk=input_dto.cashdesk,
            terminal=input_dto.terminal,
            date_from=input_dto.date_from,
            date_to=input_dto.date_to,
            limit=input_dto.limit,
            offset=input_dto.offset
        )
        total = await self._tx_repo.count_suspicious(
            train_no=input_dto.train_no,
            cashdesk=input_dto.cashdesk,
            terminal=input_dto.terminal,
            date_from=input_dto.date_from,
            date_to=input_dto.date_to
        )
        return results, total
