import { v4 as uuid } from "uuid";
import { Money } from "./money";
import { OrderStatus } from "./order-status";
import { OrderRecord } from "../infrastructure/persistence/order-record";

export class Order {
  private constructor(
    readonly id: string,
    private status: OrderStatus,
    private total: Money,
  ) {}

  static place(total: Money): Order {
    return new Order(uuid(), OrderStatus.Placed, total);
  }

  toRecord(): OrderRecord {
    return { id: this.id, status: this.status, total: this.total.amount };
  }
}
