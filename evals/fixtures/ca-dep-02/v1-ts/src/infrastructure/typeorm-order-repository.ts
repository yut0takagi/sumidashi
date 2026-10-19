import { EntityManager } from "typeorm";
import { Order } from "../domain/order";
import { OrderRepository } from "../domain/order-repository";

export class TypeOrmOrderRepository implements OrderRepository {
  async save(order: Order, manager: EntityManager): Promise<void> {
    await manager.save(order);
  }
}
