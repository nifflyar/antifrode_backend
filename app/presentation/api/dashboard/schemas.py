from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_passengers: int
    high_risk_count: int
    critical_risk_count: int
    share_suspicious_ops: float
    top_risk_channel: str | None
    top_risk_terminal: str | None


class RiskTrendItem(BaseModel):
    date: str
    total_ops: int
    highrisk_ops: int
    share: float


class RiskTrendResponse(BaseModel):
    trends: list[RiskTrendItem]


class RiskConcentrationItem(BaseModel):
    dimension_value: str
    total_ops: int
    highrisk_ops: int
    share_highrisk_ops: float
    lift_vs_base: float


class RiskConcentrationResponse(BaseModel):
    items: list[RiskConcentrationItem]
