from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ShippingRule:
    fee: Decimal
    regions: list[str]
    carriers: tuple[str, ...] = ()

    def applies_to(self, region: str) -> bool:
        return region in self.regions
