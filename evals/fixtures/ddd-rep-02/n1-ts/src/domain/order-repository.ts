import { Order } from "./order";
import { OrderSpecification } from "./order-specification";

export interface OrderSearchQuery {
  customerId?: string;
  placedAfter?: Date;
}

export interface OrderRepository {
  findById(id: string): Promise<Order | null>;
  findSatisfying(spec: OrderSpecification): Promise<Order[]>;
  search(query: OrderSearchQuery): Promise<Order[]>;
  save(order: Order): Promise<void>;
}
