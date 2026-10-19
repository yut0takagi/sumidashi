import { Order } from "./order";

export interface OrderSpecification {
  isSatisfiedBy(order: Order): boolean;
}
