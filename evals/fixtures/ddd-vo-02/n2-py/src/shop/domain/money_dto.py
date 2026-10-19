from dataclasses import dataclass


@dataclass
class MoneyDto:
    amount: str
    currency: str
