import { CouponRedeemEvent } from "../domain/events";

export function redeemCoupon(code: string, orderId: string): CouponRedeemEvent {
  return { couponCode: code, orderId, occurredAt: new Date() };
}
