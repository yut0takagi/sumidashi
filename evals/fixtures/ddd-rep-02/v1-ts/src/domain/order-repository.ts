import { EntityManager, FindOptionsWhere } from "typeorm";
import { Order } from "./order";

export interface OrderRepository {
  findById(id: string): Promise<Order | null>;
  findWhere(where: FindOptionsWhere<Order>): Promise<Order[]>;
  save(order: Order, manager?: EntityManager): Promise<void>;
}
