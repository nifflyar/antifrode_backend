from dishka import Provider, Scope, provide

from app.application.dashboard.get_summary import GetDashboardSummaryInteractor
from app.application.dashboard.get_risk_trend import GetRiskTrendInteractor
from app.application.dashboard.get_risk_concentration import GetRiskConcentrationInteractor
from app.domain.passenger.repository import IPassengerRepository
from app.domain.transaction.repository import ITransactionRepository
from app.domain.risk.repository import IRiskConcentrationRepository


class DashboardInteractorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def provide_get_dashboard_summary_interactor(
        self,
        passenger_repository: IPassengerRepository,
        transaction_repository: ITransactionRepository,
        risk_concentration_repository: IRiskConcentrationRepository,
    ) -> GetDashboardSummaryInteractor:
        return GetDashboardSummaryInteractor(
            passenger_repository,
            transaction_repository,
            risk_concentration_repository,
        )

    @provide
    def provide_get_risk_trend_interactor(
        self,
        transaction_repository: ITransactionRepository,
    ) -> GetRiskTrendInteractor:
        return GetRiskTrendInteractor(transaction_repository)

    @provide
    def provide_get_risk_concentration_interactor(
        self,
        risk_concentration_repository: IRiskConcentrationRepository,
    ) -> GetRiskConcentrationInteractor:
        return GetRiskConcentrationInteractor(risk_concentration_repository)
