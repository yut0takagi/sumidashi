from datetime import datetime


class Shipment:
    def __init__(self, shipment_id: str) -> None:
        self._id = shipment_id
        self._shipped_at: datetime | None = None

    def ship(self, at: datetime) -> None:
        if self._shipped_at is not None:
            raise ValueError("already shipped")
        self._shipped_at = at
