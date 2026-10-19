import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional


class Plan(Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class Subscription:
    plan: Plan
    expires_on: date
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: deque = field(default_factory=deque)

    def renew(self, price: Decimal, today: Optional[date] = None) -> None:
        base = max(self.expires_on, today or date.today())
        days = 30 if self.plan is Plan.MONTHLY else 365
        self.expires_on = base + timedelta(days=days)
        self.history.append(price)
