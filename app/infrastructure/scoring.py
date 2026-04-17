"""ML scoring logic - feature engineering and model."""
import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

_SUSPICIOUS_BANDS = ("HIGH", "CRITICAL")


class FeatureEngineer:
    """Feature engineering for passenger scoring - matches production script."""

    @staticmethod
    def fake_fio_score(fio) -> int:
        """
        Score fake FIO (0 = real, 1 = suspicious).

        Detects:
        - Missing names
        - Very few unique letters
        - Garbage patterns (repeated letters, test strings)
        - Names too short
        """
        if pd.isna(fio):
            return 1

        fio = str(fio).lower().strip()

        # Few unique letters - likely fake
        if len(set(fio)) <= 3:
            return 1

        # Common garbage patterns
        if any(x in fio for x in ["ааа", "иии", "bbb", "test", "qwerty", "xxx"]):
            return 1

        # Too short for a real name
        if len(fio) < 5:
            return 1

        return 0

    @staticmethod
    def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from transaction data.

        Implements exact logic from production script:
        1. Extract time features (hour, night flag, date)
        2. Aggregate by passenger
        3. Calculate derived features (refund_share, night_share)
        4. Detect seat blocking (late refunds < 24h before departure)

        Input dataframe must have columns:
        - ticket_no (transaction ID)
        - passenger_id
        - op_type ("Продажа", "Возврат")
        - op_datetime
        - dep_datetime
        - fio (passenger name)
        """
        # Ensure datetime columns are parsed
        df_work = df.copy()
        df_work["op_datetime"] = pd.to_datetime(df_work["op_datetime"], errors="coerce")
        df_work["dep_datetime"] = pd.to_datetime(df_work["dep_datetime"], errors="coerce")

        # Time features
        df_work["hour"] = df_work["op_datetime"].dt.hour
        df_work["is_night"] = df_work["hour"].between(0, 5).astype(int)
        df_work["date_only"] = df_work["op_datetime"].dt.date

        # ===== AGGREGATE BY PASSENGER =====
        agg = df_work.groupby("passenger_id").agg(
            # Basic counts
            total_tickets=("ticket_no", "count"),
            refund_cnt=("op_type", lambda x: (x == "Возврат").sum()),
            active_days=("date_only", "nunique"),
            night_tickets=("is_night", "sum"),

            # FIO - detect fake patterns
            fake_fio=("fio", lambda x: x.apply(FeatureEngineer.fake_fio_score).max()),

            # Dates
            first_date=("op_datetime", "min"),
            last_date=("op_datetime", "max"),
        ).reset_index()

        # ===== DERIVED FEATURES =====
        agg["refund_share"] = agg["refund_cnt"] / agg["total_tickets"].replace(0, 1)
        agg["night_share"] = agg["night_tickets"] / agg["total_tickets"].replace(0, 1)

        # ===== SEAT BLOCKING DETECTION =====
        # Refunds close to departure time (< 24h) indicate seat blocking
        df_work["hours_to_departure"] = (
            (df_work["dep_datetime"] - df_work["op_datetime"]).dt.total_seconds() / 3600
        )
        df_work["late_refund"] = (
            (df_work["op_type"] == "Возврат") &
            (df_work["hours_to_departure"] < 24)
        ).astype(int)

        seat_block = df_work.groupby("passenger_id").agg(
            late_refunds=("late_refund", "sum"),
        ).reset_index()

        agg = agg.merge(seat_block, on="passenger_id", how="left")
        agg["late_refunds"] = agg["late_refunds"].fillna(0)

        logger.info(
            f"Feature engineering complete: {len(agg)} passengers, "
            f"avg {agg['total_tickets'].mean():.1f} tickets/person, "
            f"avg {agg['refund_share'].mean():.1%} refund rate"
        )

        return agg

    @staticmethod
    def rule_score(row: pd.Series) -> float:
        """
        Calculate rule-based risk score (0-100).

        Scoring rules (matches production script exactly):
        - High ticket volume (>20): +20 pts
        - High refund rate (>50%): +25 pts
        - Multiple late refunds (>5): +30 pts
        - Suspicious FIO: +25 pts
        - Night operations (>50%): +10 pts

        Max score capped at 100.
        """
        score = 0

        if row["total_tickets"] > 20:
            score += 20

        if row["refund_share"] > 0.5:
            score += 25

        if row["late_refunds"] > 5:
            score += 30

        if row["fake_fio"] == 1:
            score += 25

        if row["night_share"] > 0.5:
            score += 10

        return min(score, 100)


class MLScorer:
    """ML scoring using Isolation Forest - matches production script."""

    def __init__(self, n_estimators: int = 300, contamination: float = 0.03):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=42,
        )

    def fit_and_score(self, agg: pd.DataFrame) -> pd.DataFrame:
        """
        Fit Isolation Forest model and score passengers.

        Features:
        1. total_tickets - transaction volume
        2. refund_cnt - absolute refund count
        3. refund_share - refund rate (0-1)
        4. night_share - night operations rate (0-1)
        5. late_refunds - seat blocking attempts
        6. fake_fio - suspicious name flag

        Detects multivariate anomalies and normalizes scores to 0-100.

        Returns:
            DataFrame with ml_score and ml_raw columns added
        """
        features = [
            "total_tickets",
            "refund_cnt",
            "refund_share",
            "night_share",
            "late_refunds",
            "fake_fio",
        ]

        X = agg[features].fillna(0)

        # Fit model
        self.model.fit(X)

        # Get anomaly scores (negative: lower = more anomalous)
        agg["ml_raw"] = -self.model.decision_function(X)

        # Normalize to 0-100 scale
        ml_min = agg["ml_raw"].min()
        ml_max = agg["ml_raw"].max()
        agg["ml_score"] = (
            (agg["ml_raw"] - ml_min) / (ml_max - ml_min + 1e-9)
        ) * 100

        logger.info(
            f"ML scoring complete: min={agg['ml_score'].min():.1f}, "
            f"max={agg['ml_score'].max():.1f}, "
            f"mean={agg['ml_score'].mean():.1f}"
        )

        return agg

    @staticmethod
    def risk_band(score: float) -> str:
        """
        Determine risk band from combined score.

        Bands (matches production script):
        - CRITICAL: score > 80
        - HIGH: 60 < score <= 80
        - MEDIUM: 40 < score <= 60
        - LOW: score <= 40
        """
        if score > 80:
            return "CRITICAL"
        elif score > 60:
            return "HIGH"
        elif score > 40:
            return "MEDIUM"
        else:
            return "LOW"

    @staticmethod
    def get_top_reasons(row: pd.Series, score: float) -> List[str]:
        """
        Get top risk factors for a passenger (up to 3).

        Checks which rules triggered the high risk:
        - High ticket volume
        - High refund rate
        - Seat blocking attempts
        - Suspicious FIO
        - Night operations
        """
        reasons = []

        if row["total_tickets"] > 20:
            reasons.append(f"High ticket volume ({int(row['total_tickets'])} tickets)")

        if row["refund_share"] > 0.5:
            reasons.append(f"High refund rate ({row['refund_share']:.0%})")

        if row["late_refunds"] > 5:
            reasons.append(f"Multiple late refunds ({int(row['late_refunds'])})")

        if row["fake_fio"] == 1:
            reasons.append("Suspicious FIO pattern")

        if row["night_share"] > 0.5:
            reasons.append(f"Night operations ({row['night_share']:.0%})")

        return reasons[:3]  # Top 3 reasons


class ScoringProcessor:
    """Main processor that orchestrates scoring."""

    def __init__(self, n_estimators: int = 300, contamination: float = 0.03):
        self.feature_engineer = FeatureEngineer()
        self.ml_scorer = MLScorer(n_estimators=n_estimators, contamination=contamination)

    async def process_scoring(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Process scoring for a transaction dataframe.

        Pipeline:
        1. Engineer features by passenger
        2. Calculate rule-based score (domain knowledge)
        3. Calculate ML score (Isolation Forest anomaly detection)
        4. Combine scores (50% rule + 50% ML)
        5. Assign risk bands (LOW/MEDIUM/HIGH/CRITICAL)
        6. Generate top risk reasons

        Returns:
            Dict with results, statistics, and metadata
        """
        try:
            # ===== 1. ENGINEER FEATURES =====
            agg = self.feature_engineer.engineer_features(df)
            logger.info(f"Engineered features for {len(agg)} passengers")

            # ===== 2. RULE-BASED SCORE =====
            agg["rule_score"] = agg.apply(
                self.feature_engineer.rule_score, axis=1
            )

            # ===== 3. ML SCORE =====
            agg = self.ml_scorer.fit_and_score(agg)

            # ===== 4. COMBINE SCORES =====
            # 50% rule-based + 50% ML model
            agg["final_score"] = (
                0.5 * agg["rule_score"] + 0.5 * agg["ml_score"]
            )

            # ===== 5. RISK BANDS =====
            agg["risk_band"] = agg["final_score"].apply(
                self.ml_scorer.risk_band
            )

            # ===== 6. TOP RISK REASONS =====
            agg["top_reasons"] = agg.apply(
                lambda row: self.ml_scorer.get_top_reasons(row, row["final_score"]),
                axis=1,
            )

            # ===== STATISTICS =====
            risk_distribution = agg["risk_band"].value_counts().to_dict()
            suspicious_count = len(agg[agg["risk_band"].isin(["HIGH", "CRITICAL"])])

            logger.info(
                f"Scoring results: {len(agg)} passengers, "
                f"suspicious={suspicious_count}, "
                f"distribution={risk_distribution}"
            )

            # ===== FORMAT RESULTS =====
            results = [
                {
                    "passenger_id": int(row["passenger_id"]),
                    "rule_score": float(row["rule_score"]),
                    "ml_score": float(row["ml_score"]),
                    "final_score": float(row["final_score"]),
                    "risk_band": row["risk_band"],
                    "top_reasons": row["top_reasons"],
                    "total_tickets": int(row["total_tickets"]),
                    "refund_rate": float(row["refund_share"]),
                    "late_refunds": int(row["late_refunds"]),
                    "fake_fio": int(row["fake_fio"]),
                    "night_rate": float(row["night_share"]),
                }
                for _, row in agg.iterrows()
            ]

            logger.info(
                f"✅ Scoring completed: "
                f"{len(results)} passengers scored, "
                f"{suspicious_count} suspicious (HIGH/CRITICAL)"
            )

            return {
                "results": results,
                "statistics": {
                    "passengers_scored": len(results),
                    "suspicious_count": suspicious_count,
                    "risk_distribution": risk_distribution,
                    "rows_processed": len(df),
                },
            }

        except Exception as e:
            logger.exception(f"❌ Scoring failed: {e}")
            raise
