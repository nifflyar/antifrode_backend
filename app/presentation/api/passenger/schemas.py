from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.domain.passenger.vo import RiskBand

class PassengerScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_score: float
    ml_score: float
    final_score: float
    risk_band: RiskBand
    top_reasons: List[str]
    seat_blocking_flag: bool
    is_manual: bool
    scored_at: Optional[datetime]

class PassengerFeaturesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_tickets: int
    refund_cnt: int
    refund_share: float
    night_tickets: int
    night_share: float
    max_tickets_month: int
    max_tickets_same_depday: int
    refund_close_ratio: float
    tickets_per_train_peak: float
    fio_fake_score_max: float

class PassengerListItemSchema(BaseModel):
    id: str
    fio_clean: str
    fake_fio_score: float
    last_seen_at: datetime
    risk_band: RiskBand
    final_score: float
    top_reasons: List[str] = []
    refund_cnt: int = 0
    max_tickets_month: int = 0
    seat_blocking_flag: bool = False

class PassengerListResponse(BaseModel):
    items: List[PassengerListItemSchema]
    total: int
    limit: int
    offset: int

class PassengerProfileResponse(BaseModel):
    id: str
    fio_clean: str
    fake_fio_score: float
    first_seen_at: datetime
    last_seen_at: datetime
    features: Optional[PassengerFeaturesSchema]
    score: Optional[PassengerScoreSchema]

class PassengerTransactionSchema(BaseModel):
    id: str
    op_type: str
    op_datetime: datetime
    dep_datetime: Optional[datetime]
    train_no: Optional[str]
    amount: float
    fee: float
    channel: Optional[str]
    route: Optional[str]
    fio: Optional[str]
    iin: Optional[str]
    phone: Optional[str]
    doc_no: Optional[str]
    order_no: Optional[str]
    dep_station: Optional[str]
    arr_station: Optional[str]
    terminal: Optional[str]
    cashdesk: Optional[str]
    aggregator: Optional[str]
    point_of_sale: Optional[str]
    tariff_type: Optional[str]
    service_class: Optional[str]
    gender: Optional[str]
    branch: Optional[str]
    carrier: Optional[str]
    settlement_type: Optional[str]

class RiskOverrideRequest(BaseModel):
    new_risk_band: RiskBand
    reason: str
