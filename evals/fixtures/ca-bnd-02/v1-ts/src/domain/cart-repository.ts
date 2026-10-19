import { Cart } from "./cart";

export interface CartRepository {
  findById(id: string): Promise<Cart>;
}
