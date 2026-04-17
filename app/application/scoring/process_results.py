from dataclasses import dataclass
from datetime import datetime, UTC
import logging

from app.domain.passenger.entity import PassengerFeatures, PassengerScore
from app.domain.passenger.feature_repository import IPassengerFeatureRepository
from app.domain.passenger.score_repository import IPassengerScoreRepository
from app.domain.passenger.vo import PassengerId, RiskBand
from app.domain.scoring.repository import IScoringJobRepository
from app.domain.scoring.vo import ScoringJobId
from app.infrastructure.ml_client import MlServiceClient, MlScoringResult
from app.application.common.transaction import TransactionManager

logger = logging.getLogger(__name__)

class ProcessScoringResultsInteractor:
    """Интерэктор для запуска ML-скоринга и обработки результатов.
    
    1. Вызывает ML-микросервис
    2. Сохраняет признаки в passenger_features
    3. Сохраняет результаты скоринга в passenger_scores
    """
    
    def __init__(
        self,
        ml_client: MlServiceClient,
        feature_repo: IPassengerFeatureRepository,
        score_repo: IPassengerScoreRepository,
        scoring_job_repo: IScoringJobRepository,
        transaction_manager: TransactionManager,
    ):
        self._ml_client = ml_client
        self._feature_repo = feature_repo
        self._score_repo = score_repo
        self._scoring_job_repo = scoring_job_repo
        self._tx_manager = transaction_manager

    async def execute(self, upload_id: int, job_id: ScoringJobId | None = None) -> None:
        logger.info(f"Processing scoring results for upload_id={upload_id}, job_id={job_id}")
        
        job = None
        if job_id:
            job = await self._scoring_job_repo.get_by_id(job_id)
            if job:
                job.mark_running()
                await self._scoring_job_repo.update(job)
                await self._tx_manager.commit()

        try:
            # 1. Получаем результаты от ML-сервиса
            ml_results: list[MlScoringResult] = await self._ml_client.run_scoring(upload_id)
            if not ml_results:
                logger.warning(f"No scoring results returned for upload_id={upload_id}")
                return

            features_to_save = []
            scores_to_save = []
            now = datetime.now(UTC)

            # 2. Мапим результаты в доменные модели
            for res in ml_results:
                pid = PassengerId(res.passenger_id)
                
                # Признаки
                features = PassengerFeatures(
                    total_tickets=res.total_tickets,
                    refund_cnt=res.refund_cnt,
                    refund_share=res.refund_share,
                    night_tickets=res.night_tickets,
                    night_share=res.night_share,
                    refund_close_ratio=res.refund_close_ratio,
                    fio_fake_score_max=res.fake_fio,
                    # Остальные поля можно оставить дефолтными или вычислить позже
                )
                features_to_save.append((pid, features))
                
                # Скоринг
                score = PassengerScore(
                    rule_score=res.rule_score,
                    ml_score=res.ml_score,
                    final_score=res.final_score,
                    risk_band=RiskBand(res.risk_band.lower()),
                    top_reasons=res.top_reasons,
                    seat_blocking_flag=(res.refund_close_ratio > 0.6), # Пример логики
                    scored_at=now
                )
                scores_to_save.append((pid, score))

            # 3. Сохраняем батчами
            await self._feature_repo.bulk_upsert(features_to_save)
            await self._score_repo.bulk_upsert(scores_to_save)
            
            if job:
                job.mark_done()
                await self._scoring_job_repo.update(job)
            
            await self._tx_manager.commit()
            logger.info(f"Successfully processed and saved scoring for {len(ml_results)} passengers")

        except Exception as e:
            logger.error(f"Failed to process scoring results for upload_id={upload_id}: {e}")
            await self._tx_manager.rollback()
            if job:
                try:
                    job.mark_failed(str(e))
                    await self._scoring_job_repo.update(job)
                    await self._tx_manager.commit()
                except Exception as update_error:
                    logger.error(f"Failed to update job status to FAILED: {update_error}")
            raise
