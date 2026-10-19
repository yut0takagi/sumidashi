from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    breakdown: tuple[Decimal, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", self.amount.quantize(Decimal("0.01")))

    def add(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount, self.currency, self.breakdown + (other.amount,))
