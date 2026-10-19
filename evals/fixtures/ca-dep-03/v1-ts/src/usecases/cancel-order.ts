import type { OrderRepository } from "../domain/order-repository";
import { NotFoundError } from "../presentation/http-errors";

export class CancelOrder {
  constructor(private readonly orders: OrderRepository) {}

  async execute(orderId: string): Promise<void> {
    const order = await this.orders.findById(orderId);
    if (!order) throw new NotFoundError(`order ${orderId}`);
    order.cancel();
    await this.orders.save(order);
  }
}
