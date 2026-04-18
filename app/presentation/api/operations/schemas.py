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
    dep_datetime: Optional[datetime]
    train_no: Optional[str]
    amount: float
    fee: float
    channel: Optional[str]
    terminal: Optional[str]
    cashdesk: Optional[str]
    aggregator: Optional[str]
    point_of_sale: Optional[str]
    doc_no: Optional[str]
    order_no: Optional[str]
    fio: Optional[str]
    iin: Optional[str]
    phone: Optional[str]
    dep_station: Optional[str]
    arr_station: Optional[str]
    route: Optional[str]
    tariff_type: Optional[str]
    service_class: Optional[str]
    gender: Optional[str]
    branch: Optional[str]
    carrier: Optional[str]
    settlement_type: Optional[str]
    risk_band: RiskBand

class SuspiciousOperationsResponse(BaseModel):
    items: List[SuspiciousOperationSchema]
    total: int
    limit: int
    offset: int
