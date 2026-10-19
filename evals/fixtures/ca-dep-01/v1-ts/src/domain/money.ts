export class Money {
  constructor(readonly amount: number) {}

  multiply(factor: number): Money {
    return new Money(Math.round(this.amount * factor));
  }
}
