import { Invoice } from "../domain/invoice";
import { PayInvoice } from "../application/pay-invoice";

export class InvoiceController {
  constructor(private readonly payInvoice: PayInvoice) {}

  async pay(body: { id: string; amount: number }): Promise<{ paymentId: string }> {
    const paymentId = await this.payInvoice.execute(new Invoice(body.id, body.amount));
    return { paymentId };
  }
}
