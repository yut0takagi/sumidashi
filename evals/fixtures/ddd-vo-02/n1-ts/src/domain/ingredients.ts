export class Ingredients {
  readonly items: ReadonlyArray<string>;
  readonly allergens: readonly string[];

  constructor(items: string[], allergens: string[] = []) {
    this.items = Object.freeze([...items]);
    this.allergens = Object.freeze([...allergens]);
  }

  with(item: string): Ingredients {
    return new Ingredients([...this.items, item], [...this.allergens]);
  }

  equals(other: Ingredients): boolean {
    return this.items.join(",") === other.items.join(",");
  }
}
