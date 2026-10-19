import Stripe from "stripe";
import { PaymentGateway } from "../application/ports/payment-gateway";

export class StripePaymentGateway implements PaymentGateway {
  constructor(private readonly stripe: Stripe) {}

  async charge(invoiceId: string, amount: number): Promise<string> {
    const intent = await this.stripe.paymentIntents.create({
      amount,
      currency: "jpy",
      metadata: { invoiceId },
    });
    return intent.id;
  }
}
