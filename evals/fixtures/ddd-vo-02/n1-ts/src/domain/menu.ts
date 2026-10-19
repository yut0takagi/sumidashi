import { Price } from "./price";

export class Menu {
  constructor(
    readonly id: string,
    private price: Price,
  ) {}

  reprice(price: Price): void {
    this.price = price;
  }

  equals(other: Menu): boolean {
    return this.id === other.id;
  }
}
