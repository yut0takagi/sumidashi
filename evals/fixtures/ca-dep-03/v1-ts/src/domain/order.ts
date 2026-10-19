export class Order {
  private cancelled = false;

  constructor(readonly id: string, readonly customerId: string) {}

  cancel(): void {
    if (this.cancelled) throw new Error("already cancelled");
    this.cancelled = true;
  }
}
