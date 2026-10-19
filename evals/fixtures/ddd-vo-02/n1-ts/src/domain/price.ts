export class Price {
  constructor(
    readonly amount: number,
    readonly currency: "JPY" | "USD",
  ) {}

  add(other: Price): Price {
    if (other.currency !== this.currency) throw new Error("currency mismatch");
    return new Price(this.amount + other.amount, this.currency);
  }

  equals(other: Price): boolean {
    return this.amount === other.amount && this.currency === other.currency;
  }
}
