from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.domain.passenger.vo import RiskBand

class SuspiciousOperationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    passenger_id: str
    op_type: str
    op_datetime: datetime
    train_no: Optional[str]
    amount: float
    channel: Optional[str]
    terminal: Optional[str]
    cashdesk: Optional[str]
    risk_band: RiskBand

class SuspiciousOperationsResponse(BaseModel):
    items: List[SuspiciousOperationSchema]
    total: int
    limit: int
    offset: int
