from payments.domain.payment import Payment


class InMemoryPaymentStore:
    def __init__(self) -> None:
        self._rows: dict[str, Payment] = {}

    def get(self, payment_id: str) -> Payment:
        return self._rows[payment_id]

    def save(self, payment: Payment) -> None:
        self._rows[payment._id] = payment


payment_store = InMemoryPaymentStore()
