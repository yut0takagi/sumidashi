import { Order } from "./order";

export class OrderLine {
  constructor(
    readonly order: Order,
    readonly sku: string,
    readonly quantity: number,
  ) {}
}
