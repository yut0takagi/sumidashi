import { Cart } from "../domain/cart";
import { CheckoutPresenter } from "../presentation/checkout-presenter";

export interface CheckoutResult {
  cartId: string;
  itemCount: number;
}

export class Checkout {
  constructor(private readonly presenter: CheckoutPresenter) {}

  execute(cart: Cart): string {
    const result: CheckoutResult = { cartId: cart.id, itemCount: cart.itemCount() };
    return this.presenter.render(result);
  }
}
