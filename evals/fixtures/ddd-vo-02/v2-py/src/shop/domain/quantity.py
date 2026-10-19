from dataclasses import dataclass


@dataclass(frozen=True)
class Quantity:
    value: int

    def add(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)
