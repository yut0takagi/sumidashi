from shop.application.restock import RestockPolicy


class Stock:
    def __init__(self, sku: str, quantity: int) -> None:
        self._sku = sku
        self._quantity = quantity

    def take(self, quantity: int, policy: RestockPolicy) -> None:
        if quantity > self._quantity:
            raise ValueError("insufficient stock")
        self._quantity -= quantity
        policy.on_taken(self)

    @property
    def quantity(self) -> int:
        return self._quantity
