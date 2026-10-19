import { Customer } from "../domain/customer";

export function renameCustomer(customer: Customer, name: string): Customer {
  return new Customer(customer.id, name);
}
