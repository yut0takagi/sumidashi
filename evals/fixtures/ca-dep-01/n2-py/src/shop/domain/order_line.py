from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class OrderLine:
    sku: str
    unit_price: Decimal
    quantity: int

    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity
