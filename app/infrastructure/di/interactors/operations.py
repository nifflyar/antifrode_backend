from dishka import Provider, Scope, provide

from app.application.operations.list_suspicious import ListSuspiciousOperationsInteractor
from app.domain.transaction.repository import ITransactionRepository

class OperationsInteractorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def list_suspicious(self, repo: ITransactionRepository) -> ListSuspiciousOperationsInteractor:
        return ListSuspiciousOperationsInteractor(repo)
