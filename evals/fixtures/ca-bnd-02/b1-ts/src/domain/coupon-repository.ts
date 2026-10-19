import { Coupon } from "./coupon";

export abstract class CouponRepository {
  abstract findByCode(code: string): Promise<Coupon | null>;
  abstract save(coupon: Coupon): Promise<void>;
}
