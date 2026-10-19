import { CartItem } from "./cart-item";

export class Cart {
  readonly items: CartItem[] = [];
  private readonly _coupons: string[] = [];

  constructor(readonly id: string) {}

  get coupons(): string[] {
    return this._coupons;
  }

  addItem(item: CartItem): void {
    if (item.quantity <= 0) throw new Error("quantity must be positive");
    this.items.push(item);
  }

  applyCoupon(code: string): void {
    if (this._coupons.includes(code)) return;
    this._coupons.push(code);
  }
}
