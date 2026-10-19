import { Invoice } from "../domain/invoice";
import { PaymentGateway } from "./ports/payment-gateway";

export class PayInvoice {
  constructor(private readonly gateway: PaymentGateway) {}

  async execute(invoice: Invoice): Promise<string> {
    return this.gateway.charge(invoice.id, invoice.amount);
  }
}
