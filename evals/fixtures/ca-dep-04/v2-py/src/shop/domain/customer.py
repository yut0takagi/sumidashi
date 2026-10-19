from shop.domain.loyalty import LoyaltyProgram


class Customer:
    def __init__(self, customer_id: str, program: LoyaltyProgram) -> None:
        self._id = customer_id
        self._program = program
