import uuid
from decimal import Decimal

from shop.domain.order_line import OrderLine
from .order_status import OrderStatus


class Order:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._lines: list[OrderLine] = []
        self._status = OrderStatus.PLACED

    @property
    def id(self) -> str:
        return self._id

    def total(self) -> Decimal:
        return sum((line.subtotal() for line in self._lines), Decimal("0"))
