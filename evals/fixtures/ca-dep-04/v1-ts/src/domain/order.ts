import { nextOrderNumber } from "../application/order-numbering";
import { Money } from "./money";

export class Order {
  readonly number: string;

  constructor(readonly id: string, private total: Money) {
    this.number = nextOrderNumber();
  }

  amount(): number {
    return this.total.value;
  }
}
