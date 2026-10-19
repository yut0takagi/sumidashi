export interface PaymentGateway {
  charge(invoiceId: string, amount: number): Promise<string>;
}
