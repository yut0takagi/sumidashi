from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Coupon:
    id: str
    code: str
    discount_rate: Decimal
    _redeemed: bool = field(default=False, repr=False)

    def redeem(self) -> None:
        if self._redeemed:
            raise ValueError("coupon already redeemed")
        self._redeemed = True
