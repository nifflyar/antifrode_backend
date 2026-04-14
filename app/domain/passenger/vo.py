from enum import Enum


from app.domain.common.vo.integer import PositiveInteger
from app.domain.common.vo.string import NonEmptyString


class PassengerId(PositiveInteger):
    pass


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"