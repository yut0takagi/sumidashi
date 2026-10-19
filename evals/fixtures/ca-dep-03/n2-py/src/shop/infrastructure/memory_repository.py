from shop.application.ports import ShipmentRepository
from shop.domain.shipment import Shipment


class InMemoryShipmentRepository(ShipmentRepository):
    def __init__(self) -> None:
        self._rows: dict[str, Shipment] = {}

    def get(self, shipment_id: str) -> Shipment:
        return self._rows[shipment_id]

    def save(self, shipment: Shipment) -> None:
        self._rows[shipment._id] = shipment
