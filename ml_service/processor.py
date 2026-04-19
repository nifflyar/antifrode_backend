import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import logging
from typing import List, Dict, Any
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

class ScoringProcessor:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)

    async def fetch_data(self, upload_id: int) -> pd.DataFrame:
        """Загружает транзакции для указанного upload_id из базы данных."""
        query = sa.text("""
            SELECT 
                t.*, 
                p.fio_clean, 
                p.fake_fio_score as p_fake_fio
            FROM transactions t
            JOIN passengers p ON t.passenger_id = p.id
            WHERE t.upload_id = :upload_id
        """)
        
        async with self.engine.connect() as conn:
            result = await conn.execute(query, {"upload_id": upload_id})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        return df

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Вычисляет признаки для каждого пассажира на основе его транзакций."""
        if df.empty:
            return pd.DataFrame()

        # 1. Базовая очистка и типы
        df["op_datetime"] = pd.to_datetime(df["op_datetime"])
        df["dep_datetime"] = pd.to_datetime(df["dep_datetime"])
        
        # 2. Ночные операции
        df["is_night"] = df["op_datetime"].dt.hour.between(0, 5).astype(int)
        
        # 3. Опоздавшие возвраты (в течение 24 часов до отправления)
        df["hours_to_departure"] = (df["dep_datetime"] - df["op_datetime"]).dt.total_seconds() / 3600
        df["late_refund"] = (
            (df["op_type"] == "refund") & 
            (df["hours_to_departure"] < 24) & 
            (df["hours_to_departure"] >= 0)
        ).astype(int)

        # 4. Агрегация по пассажирам
        agg = df.groupby("passenger_id").agg(
            total_tickets=("id", "count"),
            refund_cnt=("op_type", lambda x: (x.str.lower() == "refund").sum()),
            night_tickets=("is_night", "sum"),
            late_refunds=("late_refund", "sum"),
            fake_fio=("p_fake_fio", "max")
        ).reset_index()

        # 5. Производные признаки
        agg["refund_share"] = agg["refund_cnt"] / agg["total_tickets"]
        agg["night_share"] = agg["night_tickets"] / agg["total_tickets"]
        agg["refund_close_ratio"] = agg["late_refunds"] / (agg["refund_cnt"] + 1e-9)

        return agg

    def get_rule_score(self, row: pd.Series) -> float:
        """Логика базового скоринга на правилах из ноутбука."""
        score = 0
        if row["total_tickets"] > 20: score += 20
        if row["refund_share"] > 0.5: score += 25
        if row["late_refunds"] > 5: score += 30
        if row["fake_fio"] > 0.5: score += 25 # Предполагаем, что 1 - это фейк
        if row["night_share"] > 0.5: score += 10
        return float(min(score, 100))

    def run_ml_model(self, agg: pd.DataFrame) -> pd.DataFrame:
        """Запуск Isolation Forest для поиска аномалий."""
        features = [
            "total_tickets", "refund_cnt", "refund_share", 
            "night_share", "late_refunds", "fake_fio"
        ]
        
        X = agg[features].fillna(0)
        
        model = IsolationForest(
            n_estimators=300,
            contamination=0.03,
            random_state=42
        )
        
        model.fit(X)
        
        # Чем меньше score_samples, тем более аномален объект
        # Мы инвертируем и нормализуем до 0-100
        raw_scores = -model.decision_function(X)
        
        min_s, max_s = raw_scores.min(), raw_scores.max()
        if max_s - min_s > 0:
            agg["ml_score"] = ((raw_scores - min_s) / (max_s - min_s)) * 100
        else:
            agg["ml_score"] = 0.0
            
        return agg

    def get_risk_band(self, score: float) -> str:
        if score > 75: return "critical"
        if score > 50: return "high"
        if score > 30: return "medium"
        return "low"

    async def process(self, upload_id: int) -> List[Dict[str, Any]]:
        """Полный цикл обработки."""
        df = await self.fetch_data(upload_id)
        if df.empty:
            return []

        agg = self.calculate_features(df)
        agg["rule_score"] = agg.apply(self.get_rule_score, axis=1)
        agg = self.run_ml_model(agg)
        
        agg["final_score"] = 0.5 * agg["rule_score"] + 0.5 * agg["ml_score"]
        agg["risk_band"] = agg["final_score"].apply(self.get_risk_band)
        
        # Сбор причин
        def get_reasons(row):
            reasons = []
            if row["total_tickets"] > 20: reasons.append("High ticket count")
            if row["refund_share"] > 0.5: reasons.append("High refund share")
            if row["late_refunds"] > 5: reasons.append("Multiple late refunds")
            if row["fake_fio"] > 0.5: reasons.append("Suspicious name pattern")
            if row["ml_score"] > 80: reasons.append("ML anomaly detected")
            return reasons

        agg["top_reasons"] = agg.apply(get_reasons, axis=1)
        
        return agg.to_dict(orient="records")
