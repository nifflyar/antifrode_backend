import logging
from dataclasses import dataclass
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.infrastructure.scoring import ScoringProcessor
from app.infrastructure.data_parser import TransactionDataParser
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MLJobResponse:
    """Response from ML service when scoring job is initiated."""
    job_id: str


@dataclass
class MLScoringItem:
    """Single scoring result from ML service."""
    passenger_id: int
    ml_score: float
    risk_band: str
    top_reasons: list[str]


@dataclass
class MLScoringResult:
    """Complete scoring result from ML service."""
    job_id: str
    status: str
    results: list[MLScoringItem]


class MlServiceClient:
    """Local ML scoring client - processes scoring within the application."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        n_estimators: int = 300,
        contamination: float = 0.03,
    ):
        self.session_maker = session_maker
        self.processor = ScoringProcessor(
            n_estimators=n_estimators,
            contamination=contamination,
        )

    async def run_scoring(self, upload_id: int) -> MLJobResponse:
        """
        Run ML scoring for an upload.

        Fetches transactions from database, processes them, and returns results.

        Args:
            upload_id: ID of the upload to score

        Returns:
            MLJobResponse with a job_id
        """
        import uuid
        job_id = str(uuid.uuid4())

        try:
            async with self.session_maker() as session:
                # Fetch transactions for this upload
                query = text("""
                    SELECT
                        id, passenger_id,
                        id as ticket_no,
                        op_type, op_datetime, dep_datetime,
                        fio,
                        train_no as dep_station,
                        amount as price, fee as fees
                    FROM transactions
                    WHERE upload_id = :upload_id
                    ORDER BY op_datetime DESC
                """)
                result = await session.execute(query, {"upload_id": upload_id})
                transactions = result.fetchall()

                if not transactions:
                    logger.warning(f"No transactions found for upload {upload_id}")
                    return MLJobResponse(job_id=job_id)

                # Convert to DataFrame
                column_names = [
                    "id", "passenger_id", "ticket_no",
                    "op_type", "op_datetime", "dep_datetime",
                    "fio",
                    "dep_station",
                    "price", "fees"
                ]
                df_raw = pd.DataFrame(
                    [dict(zip(column_names, row)) for row in transactions]
                )

                logger.info(f"Fetched {len(df_raw)} transactions for upload {upload_id}")

                # Parse and clean data
                df_clean, parse_metadata = TransactionDataParser.parse_dataframe(
                    df_raw, auto_match=False
                )

                # Filter to valid operation types
                if "op_type" in df_clean.columns:
                    df_clean = df_clean[
                        df_clean["op_type"].isin(["Продажа", "Возврат"])
                    ]

                logger.info(f"After cleaning: {len(df_clean)} transactions")

                if len(df_clean) == 0:
                    logger.warning(f"No valid transactions after cleaning for upload {upload_id}")
                    return MLJobResponse(job_id=job_id)

                # Process scoring
                await self.processor.process_scoring(df_clean)

            logger.info(f"ML scoring completed for upload {upload_id}: job_id={job_id}")
            return MLJobResponse(job_id=job_id)

        except Exception as e:
            logger.error(f"Failed to run ML scoring for upload {upload_id}: {e}")
            raise

    async def get_scoring_result(self, job_id: str, upload_id: int) -> MLScoringResult:
        """
        Get scoring results for an upload.

        Re-processes the scoring to generate results (since we process locally).

        Args:
            job_id: Job ID (for compatibility)
            upload_id: ID of the upload

        Returns:
            MLScoringResult with list of scored passengers
        """
        try:
            async with self.session_maker() as session:
                # Fetch transactions
                query = text("""
                    SELECT
                        id, passenger_id,
                        id as ticket_no,
                        op_type, op_datetime, dep_datetime,
                        fio,
                        train_no as dep_station,
                        amount as price, fee as fees
                    FROM transactions
                    WHERE upload_id = :upload_id
                    ORDER BY op_datetime DESC
                """)
                result = await session.execute(query, {"upload_id": upload_id})
                transactions = result.fetchall()

                if not transactions:
                    return MLScoringResult(
                        job_id=job_id,
                        status="DONE",
                        results=[],
                    )

                # Convert to DataFrame
                column_names = [
                    "id", "passenger_id", "ticket_no",
                    "op_type", "op_datetime", "dep_datetime",
                    "fio",
                    "dep_station",
                    "price", "fees"
                ]
                df_raw = pd.DataFrame(
                    [dict(zip(column_names, row)) for row in transactions]
                )

                # Parse and clean data
                df_clean, parse_metadata = TransactionDataParser.parse_dataframe(
                    df_raw, auto_match=False
                )

                # Filter to valid operation types
                if "op_type" in df_clean.columns:
                    df_clean = df_clean[
                        df_clean["op_type"].isin(["Продажа", "Возврат"])
                    ]

                if len(df_clean) == 0:
                    return MLScoringResult(
                        job_id=job_id,
                        status="DONE",
                        results=[],
                    )

                # Process scoring
                scoring_output = await self.processor.process_scoring(df_clean)

                # Convert results to MLScoringItem objects
                results = [
                    MLScoringItem(
                        passenger_id=item["passenger_id"],
                        ml_score=item["ml_score"],
                        risk_band=item["risk_band"],
                        top_reasons=item.get("top_reasons", []),
                    )
                    for item in scoring_output["results"]
                ]

                logger.info(f"ML scoring results retrieved for job {job_id}: {len(results)} passengers")
                return MLScoringResult(
                    job_id=job_id,
                    status="DONE",
                    results=results,
                )

        except Exception as e:
            logger.error(f"Failed to get ML scoring results for job {job_id}: {e}")
            raise
