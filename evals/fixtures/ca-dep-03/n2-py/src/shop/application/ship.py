from shop.domain.shipment import Shipment
from shop.shared.clock import utcnow
from .ports import ShipmentRepository


def ship(repo: ShipmentRepository, shipment_id: str) -> Shipment:
    shipment = repo.get(shipment_id)
    shipment.ship(utcnow())
    repo.save(shipment)
    return shipment
