from app.domain.transaction.repository import ITransactionRepository
from app.domain.transaction.entity import Transaction
from app.domain.passenger.vo import PassengerId

class GetPassengerTransactionsInteractor:
    def __init__(self, repository: ITransactionRepository) -> None:
        self._repo = repository

    async def execute(
        self, 
        passenger_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> list[Transaction]:
        return await self._repo.get_by_passenger_id(
            PassengerId(passenger_id), 
            limit=limit, 
            offset=offset
        )
