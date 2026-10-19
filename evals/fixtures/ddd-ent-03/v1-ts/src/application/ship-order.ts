import { Order } from "../domain/order";
import { OrderStatus } from "../domain/order-status";

export function shipOrder(order: Order): void {
  order.setStatus(OrderStatus.Shipped);
}
