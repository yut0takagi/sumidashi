import { Order } from "../domain/order";
import { PostgresOrderRepository } from "../infrastructure/postgres-order-repository";

export class PlaceOrder {
  private readonly orders = new PostgresOrderRepository();

  async execute(orderId: string, customerId: string): Promise<Order> {
    const order = new Order(orderId, customerId);
    await this.orders.save(order);
    return order;
  }
}
