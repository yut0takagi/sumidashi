from typing import Protocol

from payments.domain.payment import Payment


class PaymentRepository(Protocol):
    def get(self, payment_id: str) -> Payment: ...

    def save(self, payment: Payment) -> None: ...
