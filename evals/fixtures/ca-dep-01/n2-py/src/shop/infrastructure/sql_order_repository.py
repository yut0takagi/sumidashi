from shop.domain.order import Order


class SqlOrderRepository:
    def __init__(self, session) -> None:
        self._session = session

    def add(self, order: Order) -> None:
        self._session.add(order)

    def get(self, order_id: str) -> Order:
        return self._session.get(Order, order_id)
