import type { EntityManager } from "typeorm";
import { Order } from "./order";

export interface OrderRepository {
  save(order: Order, manager: EntityManager): Promise<void>;
}
