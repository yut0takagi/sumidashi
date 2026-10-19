import { Order } from "../domain/order";

export function addToOrder(order: Order, sku: string): void {
  order.add(sku, 1);
}
