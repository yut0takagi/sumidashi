import { writeFileSync } from "fs";
import { Order } from "./order";

export function printReceipt(order: Order, path: string): void {
  writeFileSync(path, `order ${order.id}`);
}
