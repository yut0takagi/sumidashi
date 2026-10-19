import { Entity, PrimaryColumn, Column } from "typeorm";
import { v4 as uuid } from "uuid";
import Decimal from "decimal.js";

@Entity("orders")
export class Order {
  @PrimaryColumn()
  readonly id: string = uuid();

  @Column("decimal")
  private total = new Decimal(0);

  addAmount(amount: Decimal): void {
    this.total = this.total.plus(amount);
  }
}
