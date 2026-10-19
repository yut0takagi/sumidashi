import type { OrderRepository } from "../domain/order-repository";

export class ShipOrder {
  constructor(private readonly orders: OrderRepository) {}

  async execute(orderId: string): Promise<boolean> {
    const order = await this.orders.findById(orderId);
    return order !== null;
  }
}
