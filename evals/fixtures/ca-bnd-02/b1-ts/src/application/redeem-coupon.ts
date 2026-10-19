import { Injectable } from "@nestjs/common";
import { ConflictException, NotFoundException } from "@nestjs/common";
import { CouponRepository } from "../domain/coupon-repository";

@Injectable()
export class RedeemCoupon {
  constructor(private readonly coupons: CouponRepository) {}

  async execute(code: string): Promise<void> {
    const coupon = await this.coupons.findByCode(code);
    if (!coupon) throw new NotFoundException(`coupon ${code}`);
    if (coupon.isRedeemed()) throw new ConflictException("already redeemed");
    coupon.redeem();
    await this.coupons.save(coupon);
  }
}
