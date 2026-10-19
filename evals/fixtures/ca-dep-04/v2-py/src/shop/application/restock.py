from shop.domain.stock import Stock


class RestockPolicy:
    def __init__(self, threshold: int) -> None:
        self._threshold = threshold
        self.requests: list[str] = []

    def on_taken(self, stock: Stock) -> None:
        if stock.quantity < self._threshold:
            self.requests.append("restock")
