class Order:
    def __init__(self, order_id: str) -> None:
        self._id = order_id

    @property
    def id(self) -> str:
        return self._id
