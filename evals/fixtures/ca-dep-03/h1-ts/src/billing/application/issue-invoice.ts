import { Invoice } from "../domain/invoice";
import { StripeGateway } from "../infra/stripe-gateway";

export class IssueInvoice {
  constructor(private readonly gateway: StripeGateway) {}

  async execute(id: string, amount: number): Promise<Invoice> {
    const invoice = new Invoice(id, amount);
    await this.gateway.createInvoice(invoice.id, invoice.amount);
    return invoice;
  }
}
