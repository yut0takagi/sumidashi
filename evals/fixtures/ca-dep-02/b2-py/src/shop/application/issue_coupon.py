from pydantic import BaseModel

from shop.domain.coupon import Coupon


class IssueCouponCommand(BaseModel):
    code: str
    discount_rate: str
    expires_on: str


def issue_coupon(command: IssueCouponCommand) -> Coupon:
    return Coupon.model_validate(command.model_dump())
