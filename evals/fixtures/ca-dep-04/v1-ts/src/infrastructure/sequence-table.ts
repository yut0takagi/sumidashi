import { Order } from "../domain/order";

export class SequenceTable {
  private readonly counters = new Map<string, number>();

  next(name: string): number {
    const value = (this.counters.get(name) ?? 0) + 1;
    this.counters.set(name, value);
    return value;
  }

  lastOrderNumber(orders: Order[]): string | undefined {
    return orders.at(-1)?.number;
  }
}
