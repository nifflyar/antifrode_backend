from dataclasses import dataclass

from app.application.common.interactor import Interactor
from app.domain.passenger.vo import PassengerId
from app.domain.transaction.repository import ITransactionRepository


@dataclass
class GetPassengerOperationsInputDTO:
    passenger_id: int
    limit: int = 100
    offset: int = 0


@dataclass
class PassengerOperationDTO:
    transaction_id: int
    source: str
    op_type: str
    op_datetime: str
    dep_datetime: str | None
    train_no: str | None
    channel: str | None
    aggregator: str | None
    terminal: str | None
    cashdesk: str | None
    point_of_sale: str | None
    amount: float
    fee: float
    fio: str
    iin: str | None
    doc_no: str | None


@dataclass
class GetPassengerOperationsOutputDTO:
    passenger_id: int
    operations: list[PassengerOperationDTO]
    limit: int
    offset: int


class GetPassengerOperationsInteractor(
    Interactor[GetPassengerOperationsInputDTO, GetPassengerOperationsOutputDTO]
):
    def __init__(self, transaction_repository: ITransactionRepository) -> None:
        self.transaction_repository = transaction_repository

    async def __call__(self, data: GetPassengerOperationsInputDTO) -> GetPassengerOperationsOutputDTO:
        # Validate limits
        if data.limit > 500:
            data.limit = 500
        if data.limit < 1:
            data.limit = 1

        # Fetch transactions
        transactions = await self.transaction_repository.get_by_passenger_id(
            PassengerId(data.passenger_id),
            limit=data.limit,
            offset=data.offset,
        )

        # Convert to output DTOs
        output_operations = [
            PassengerOperationDTO(
                transaction_id=tx.id.value,
                source=tx.source,
                op_type=tx.op_type.value,
                op_datetime=tx.op_datetime.isoformat(),
                dep_datetime=tx.dep_datetime.isoformat() if tx.dep_datetime else None,
                train_no=tx.train_no,
                channel=tx.channel,
                aggregator=tx.aggregator,
                terminal=tx.terminal,
                cashdesk=tx.cashdesk,
                point_of_sale=tx.point_of_sale,
                amount=tx.amount,
                fee=tx.fee,
                fio=tx.fio,
                iin=tx.iin,
                doc_no=tx.doc_no,
            )
            for tx in transactions
        ]

        return GetPassengerOperationsOutputDTO(
            passenger_id=data.passenger_id,
            operations=output_operations,
            limit=data.limit,
            offset=data.offset,
        )
