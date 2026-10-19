import { Order } from "../domain/order";
import { OrderRepository } from "../domain/order-repository";

export class InMemoryOrderRepository implements OrderRepository {
  private readonly rows = new Map<string, Order>();

  async findById(id: string): Promise<Order | null> {
    return this.rows.get(id) ?? null;
  }

  async save(order: Order): Promise<void> {
    this.rows.set(order.id, order);
  }
}
