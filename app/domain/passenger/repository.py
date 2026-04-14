
# app/domain/passenger/repository.py
from abc import ABC, abstractmethod
from app.domain.passenger.entity import Passenger
from app.domain.passenger.vo import PassengerId, RiskBand

class IPassengerRepository(ABC):

    @abstractmethod
    async def get_by_id(self, passenger_id: PassengerId) -> Passenger | None: ...

    @abstractmethod
    async def get_all(
        self,
        risk_band: RiskBand | None = None,
        channel: str | None = None,
        cashdesk: str | None = None,
        terminal: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        seat_blocking_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Passenger]: ...

    @abstractmethod
    async def count(self, risk_band: RiskBand | None = None) -> int: ...

    @abstractmethod
    async def create_passenger(self, passenger: Passenger) -> None: ...

    @abstractmethod
    async def update_passenger(self, passenger: Passenger) -> None: ...

    @abstractmethod
    async def delete_passenger(self, passenger_id: PassengerId) -> None: ...