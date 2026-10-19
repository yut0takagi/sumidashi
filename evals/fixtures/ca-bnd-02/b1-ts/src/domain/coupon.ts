export class Coupon {
  private redeemed = false;

  constructor(readonly code: string) {}

  isRedeemed(): boolean {
    return this.redeemed;
  }

  redeem(): void {
    this.redeemed = true;
  }
}
