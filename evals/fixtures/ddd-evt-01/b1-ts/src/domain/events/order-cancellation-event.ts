import { DomainEvent } from "./domain-event";

export class OrderCancellationEvent extends DomainEvent {
  constructor(readonly orderId: string) {
    super();
  }
}
