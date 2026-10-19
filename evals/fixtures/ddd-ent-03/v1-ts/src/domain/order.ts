import { OrderStatus } from "./order-status";

export class Order {
  static readonly MAX_LINES = 50;

  status: OrderStatus;
  public shippingAddress: string;
  private cancelledAt: Date | null = null;
  private _note = "";

  constructor(readonly id: string, shippingAddress: string) {
    this.status = OrderStatus.Pending;
    this.shippingAddress = shippingAddress;
  }

  get note(): string {
    return this._note;
  }

  set note(value: string) {
    this._note = value;
  }

  setStatus(status: OrderStatus): void {
    this.status = status;
  }

  cancel(at: Date): void {
    if (this.status === OrderStatus.Shipped) {
      throw new Error("shipped orders cannot be cancelled");
    }
    this.status = OrderStatus.Cancelled;
    this.cancelledAt = at;
  }
}
