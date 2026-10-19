export class Cart {
  constructor(
    readonly id: string,
    private readonly prices: number[],
  ) {}

  total(): number {
    return this.prices.reduce((sum, p) => sum + p, 0);
  }
}
