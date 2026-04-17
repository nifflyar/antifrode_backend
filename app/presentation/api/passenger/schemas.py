from pydantic import BaseModel, Field
from typing import Optional


class PassengerListItemSchema(BaseModel):
    passenger_id: int
    final_score: float
    risk_band: str
    top_reasons: list[str]
    refund_cnt: int
    max_tickets_month: int
    seat_blocking_flag: bool


class PassengerListResponseSchema(BaseModel):
    passengers: list[PassengerListItemSchema]
    total: int
    limit: int
    offset: int


class PassengerFeatureSchema(BaseModel):
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


class PassengerScoreSchema(BaseModel):
    rule_score: float
    ml_score: float
    final_score: float
    risk_band: str
    top_reasons: list[str]
    seat_blocking_flag: bool


class PassengerProfileResponseSchema(BaseModel):
    passenger_id: int
    fio_clean: str
    fake_fio_score: float
    first_seen_at: str
    last_seen_at: str
    score: Optional[PassengerScoreSchema] = None
    features: Optional[PassengerFeatureSchema] = None


class PassengerOperationSchema(BaseModel):
    transaction_id: int
    source: str
    op_type: str
    op_datetime: str
    dep_datetime: Optional[str] = None
    train_no: Optional[str] = None
    channel: Optional[str] = None
    aggregator: Optional[str] = None
    terminal: Optional[str] = None
    cashdesk: Optional[str] = None
    point_of_sale: Optional[str] = None
    amount: float
    fee: float
    fio: str
    iin: Optional[str] = None
    doc_no: Optional[str] = None


class PassengerOperationsResponseSchema(BaseModel):
    passenger_id: int
    operations: list[PassengerOperationSchema]
    limit: int
    offset: int
