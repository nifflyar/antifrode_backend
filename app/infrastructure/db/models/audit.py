from datetime import datetime

from sqlalchemy import TIMESTAMP, String, func, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.base import BaseORMModel


class AuditLogModel(BaseORMModel):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
