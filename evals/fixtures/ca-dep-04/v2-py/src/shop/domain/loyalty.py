from shop.domain.customer import Customer


class LoyaltyProgram:
    def points_for(self, customer: Customer, amount: int) -> int:
        return amount // 100
