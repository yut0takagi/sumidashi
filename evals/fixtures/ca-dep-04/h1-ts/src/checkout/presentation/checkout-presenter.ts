import { CheckoutResult } from "../application/checkout";

export class CheckoutPresenter {
  render(result: CheckoutResult): string {
    return JSON.stringify({ cart: result.cartId, items: result.itemCount });
  }
}
