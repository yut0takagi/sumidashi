class Warehouse:
    def __init__(self, warehouse_id: str, name: str) -> None:
        self.warehouse_id = warehouse_id
        self.name = name
        self._status = "open"
        self._capacity = 0

    def set_status(self, status: str) -> None:
        self._status = status

    def expand(self, units: int) -> None:
        if units <= 0:
            raise ValueError("units must be positive")
        self._capacity += units
