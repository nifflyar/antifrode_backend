from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.infrastructure.ml_client import MlServiceClient


class MlProvider(Provider):
    scope = Scope.APP

    @provide(scope=Scope.APP)
    def get_ml_client(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> MlServiceClient:
        """
        Provide local ML scoring client.

        The client is created as a singleton (APP scope) so the ML model is reused.
        """
        return MlServiceClient(session_maker=session_maker)
