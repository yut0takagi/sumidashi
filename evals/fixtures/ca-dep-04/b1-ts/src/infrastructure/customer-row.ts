import { Customer } from "../domain/customer";

export interface CustomerRow {
  id: string;
  display_name: string;
}

export function toRow(customer: Customer): CustomerRow {
  return { id: customer.id, display_name: customer.name };
}
