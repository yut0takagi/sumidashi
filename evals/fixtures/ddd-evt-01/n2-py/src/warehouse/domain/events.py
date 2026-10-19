from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationEvent:
    aggregate_id: str


@dataclass(frozen=True)
class StockReserved(IntegrationEvent):
    quantity: int


@dataclass(frozen=True)
class ShipmentSent(IntegrationEvent):
    carrier: str


@dataclass(frozen=True)
class ReservationMade(IntegrationEvent):
    reserved_by: str


@dataclass(frozen=True)
class StockTaken(IntegrationEvent):
    quantity: int
