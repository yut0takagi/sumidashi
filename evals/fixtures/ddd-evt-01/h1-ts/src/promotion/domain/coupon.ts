import { CouponIssued } from "./events";

export class Coupon {
  constructor(readonly code: string) {}

  issue(): CouponIssued {
    return { couponCode: this.code, occurredAt: new Date() };
  }
}
