export class Invoice {
  private paidAt: Date | null = null;

  constructor(readonly id: string, readonly amount: number) {}

  markPaid(at: Date): void {
    if (this.paidAt) throw new Error("already paid");
    this.paidAt = at;
  }
}
