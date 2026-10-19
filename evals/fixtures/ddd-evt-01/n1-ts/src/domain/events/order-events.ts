import { DomainEvent } from "./domain-event";

export class OrderPlaced extends DomainEvent {
  constructor(readonly orderId: string) {
    super();
  }
}

export class ItemAddedToCart extends DomainEvent {
  constructor(
    readonly cartId: string,
    readonly sku: string,
  ) {
    super();
  }
}

export class OrderPaidEvent extends DomainEvent {
  constructor(readonly orderId: string) {
    super();
  }
}

export class InvoiceSentV2Event extends DomainEvent {
  constructor(
    readonly invoiceId: string,
    readonly channel: "email" | "post",
  ) {
    super();
  }
}
