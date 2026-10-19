class Stock:
    def __init__(self, sku: str, quantity: int) -> None:
        self._sku = sku
        self._quantity = quantity

    @property
    def sku(self) -> str:
        return self._sku

    def reserve(self, quantity: int) -> None:
        if quantity > self._quantity:
            raise ValueError("insufficient stock")
        self._quantity -= quantity
