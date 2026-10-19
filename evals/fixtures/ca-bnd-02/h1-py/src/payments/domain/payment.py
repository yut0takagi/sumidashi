from decimal import Decimal


class Payment:
    def __init__(self, payment_id: str, amount: Decimal) -> None:
        self._id = payment_id
        self._amount = amount
        self._refunded = Decimal("0")

    def refund(self, amount: Decimal) -> None:
        if self._refunded + amount > self._amount:
            raise ValueError("refund exceeds payment")
        self._refunded += amount
