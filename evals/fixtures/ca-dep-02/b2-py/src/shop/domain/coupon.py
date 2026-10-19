from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator


class Coupon(BaseModel):
    code: str
    discount_rate: Decimal
    expires_on: date

    @field_validator("discount_rate")
    @classmethod
    def rate_must_be_fraction(cls, value: Decimal) -> Decimal:
        if not (Decimal("0") < value < Decimal("1")):
            raise ValueError("discount_rate must be between 0 and 1")
        return value
