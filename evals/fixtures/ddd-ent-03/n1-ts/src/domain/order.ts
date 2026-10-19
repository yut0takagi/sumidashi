import { OrderLine } from "./order-line";

export class Order {
  #lines: OrderLine[] = [];
  private _shippingAddress: string;
  readonly tags: ReadonlyArray<string>;

  constructor(
    readonly id: string,
    shippingAddress: string,
    tags: string[],
  ) {
    this._shippingAddress = shippingAddress;
    this.tags = [...tags];
  }

  get lines(): readonly OrderLine[] {
    return [...this.#lines];
  }

  get shippingAddress(): string {
    return this._shippingAddress;
  }

  set shippingAddress(value: string) {
    if (value.trim() === "") throw new Error("shipping address is required");
    this._shippingAddress = value;
  }

  addLine(line: OrderLine): void {
    if (this.#lines.length >= 50) throw new Error("too many lines");
    this.#lines.push(line);
  }
}
