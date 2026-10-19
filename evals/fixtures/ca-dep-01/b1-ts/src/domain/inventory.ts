import type { StockRow } from "../infrastructure/stock-row";
import { Sku } from "./sku";

export class Inventory {
  constructor(
    readonly sku: Sku,
    private onHand: number,
  ) {}

  static fromRow(row: StockRow): Inventory {
    return new Inventory(new Sku(row.sku), row.on_hand);
  }

  available(): number {
    return this.onHand;
  }
}
