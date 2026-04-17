from dishka import Provider, Scope, provide

from app.application.passenger.list_passengers import ListPassengersInteractor
from app.application.passenger.get_passenger import GetPassengerInteractor
from app.application.passenger.get_passenger_operations import GetPassengerOperationsInteractor
from app.domain.passenger.repository import IPassengerRepository
from app.domain.transaction.repository import ITransactionRepository


class PassengerInteractorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def provide_list_passengers_interactor(
        self,
        passenger_repository: IPassengerRepository,
        transaction_repository: ITransactionRepository,
    ) -> ListPassengersInteractor:
        return ListPassengersInteractor(passenger_repository, transaction_repository)

    @provide
    def provide_get_passenger_interactor(
        self,
        passenger_repository: IPassengerRepository,
    ) -> GetPassengerInteractor:
        return GetPassengerInteractor(passenger_repository)

    @provide
    def provide_get_passenger_operations_interactor(
        self,
        transaction_repository: ITransactionRepository,
    ) -> GetPassengerOperationsInteractor:
        return GetPassengerOperationsInteractor(transaction_repository)
