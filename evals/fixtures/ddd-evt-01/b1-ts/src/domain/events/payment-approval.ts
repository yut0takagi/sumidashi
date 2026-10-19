import { DomainEvent } from "./domain-event";

export class PaymentApproval extends DomainEvent {
  constructor(
    readonly paymentId: string,
    readonly approvedBy: string,
  ) {
    super();
  }
}
