export class Cart {
  private readonly items = new Map<string, number>();

  constructor(readonly id: string) {}

  add(sku: string, quantity: number): void {
    this.items.set(sku, (this.items.get(sku) ?? 0) + quantity);
  }

  itemCount(): number {
    return [...this.items.values()].reduce((a, b) => a + b, 0);
  }
}
