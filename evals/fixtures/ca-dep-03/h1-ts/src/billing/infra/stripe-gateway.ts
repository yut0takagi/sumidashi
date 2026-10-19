import Stripe from "stripe";

export class StripeGateway {
  constructor(private readonly stripe: Stripe) {}

  async createInvoice(id: string, amount: number): Promise<void> {
    await this.stripe.invoiceItems.create({
      customer: id,
      amount,
      currency: "jpy",
    });
  }
}
