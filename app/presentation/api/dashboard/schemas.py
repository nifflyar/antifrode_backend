from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class DashboardSummaryResponse(BaseModel):
    total_passengers: int
    high_risk_count: int
    critical_risk_count: int
    share_suspicious_ops: float
    top_risk_channel: Optional[str] = None
    top_risk_terminal: Optional[str] = None

class RiskTrendItem(BaseModel):
    date: datetime
    total_ops: int
    highrisk_ops: int
    share: float

class RiskTrendResponse(BaseModel):
    items: List[RiskTrendItem]

class RiskConcentrationItem(BaseModel):
    dimension_value: str
    total_ops: int
    highrisk_ops: int
    share_highrisk_ops: float
    lift_vs_base: float

class RiskConcentrationResponse(BaseModel):
    dimension_type: str
    items: List[RiskConcentrationItem]
