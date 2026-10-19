import { OrderLine } from "./order-line";

export class Order {
  private readonly lines: OrderLine[] = [];

  constructor(readonly id: string) {}

  add(sku: string, quantity: number): void {
    this.lines.push(new OrderLine(this, sku, quantity));
  }
}
