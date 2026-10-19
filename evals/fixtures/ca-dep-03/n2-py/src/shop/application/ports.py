from typing import Protocol

from shop.domain.shipment import Shipment


class ShipmentRepository(Protocol):
    def get(self, shipment_id: str) -> Shipment: ...

    def save(self, shipment: Shipment) -> None: ...
