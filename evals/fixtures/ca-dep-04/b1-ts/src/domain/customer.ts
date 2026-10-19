import type { CustomerRow } from "../infrastructure/customer-row";

export class Customer {
  constructor(
    readonly id: string,
    readonly name: string,
  ) {}

  static fromRow(row: CustomerRow): Customer {
    return new Customer(row.id, row.display_name);
  }
}
