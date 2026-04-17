from dishka import Provider, Scope, provide

from app.application.scoring.process_results import ProcessScoringResultsInteractor
from app.application.scoring.run_scoring import RunScoringInteractor
from app.application.scoring.get_scoring_status import GetScoringStatusInteractor
from app.application.scoring.execute_scoring import ExecuteScoringInteractor
from app.application.common.transaction import TransactionManager
from app.domain.passenger.score_repository import IPassengerScoreRepository
from app.domain.risk.repository import IRiskConcentrationRepository
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.audit.repository import IAuditLogRepository
from app.infrastructure.ml_client import MlServiceClient


class ScoringProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def provide_process_scoring_results_interactor(
        self,
        passenger_score_repository: IPassengerScoreRepository,
        risk_concentration_repository: IRiskConcentrationRepository,
        transaction_manager: TransactionManager,
    ) -> ProcessScoringResultsInteractor:
        return ProcessScoringResultsInteractor(
            passenger_score_repository=passenger_score_repository,
            risk_concentration_repository=risk_concentration_repository,
            transaction_manager=transaction_manager,
        )

    @provide
    def provide_run_scoring_interactor(
        self,
        scoring_job_repository: IScoringJobRepository,
        audit_log_repository: IAuditLogRepository,
        transaction_manager: TransactionManager,
    ) -> RunScoringInteractor:
        return RunScoringInteractor(
            scoring_job_repository=scoring_job_repository,
            audit_log_repository=audit_log_repository,
            transaction_manager=transaction_manager,
        )

    @provide
    def provide_get_scoring_status_interactor(
        self,
        scoring_job_repository: IScoringJobRepository,
    ) -> GetScoringStatusInteractor:
        return GetScoringStatusInteractor(
            scoring_job_repository=scoring_job_repository,
        )

    @provide
    def provide_execute_scoring_interactor(
        self,
        ml_client: MlServiceClient,
        process_results_interactor: ProcessScoringResultsInteractor,
        scoring_job_repository: IScoringJobRepository,
        transaction_manager: TransactionManager,
    ) -> ExecuteScoringInteractor:
        return ExecuteScoringInteractor(
            ml_client=ml_client,
            process_results_interactor=process_results_interactor,
            scoring_job_repository=scoring_job_repository,
            transaction_manager=transaction_manager,
        )


