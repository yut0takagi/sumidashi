export class Money {
  constructor(
    readonly amount: number,
    public currency: string,
  ) {}

  equals(other: Money): boolean {
    return this.amount === other.amount && this.currency === other.currency;
  }
}
