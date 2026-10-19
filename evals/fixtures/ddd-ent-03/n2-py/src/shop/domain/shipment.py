from dataclasses import dataclass


@dataclass(frozen=True)
class Shipment:
    id: str
    destination: str
