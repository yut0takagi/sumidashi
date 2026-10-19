import { Percentage } from "../domain/percentage";

export function applyDiscount(price: number, discount: Percentage): number {
  return Math.round(price * (1 - discount.rate / 100));
}
