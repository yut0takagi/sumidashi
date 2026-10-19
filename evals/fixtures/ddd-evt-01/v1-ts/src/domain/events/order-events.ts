import { DomainEvent } from "./domain-event";

export class OrderPlacedEvent extends DomainEvent {
  constructor(readonly orderId: string) {
    super();
  }
}

export class PlaceOrderEvent extends DomainEvent {
  constructor(readonly orderId: string) {
    super();
  }
}

export class OrderCancelEvent extends DomainEvent {
  constructor(
    readonly orderId: string,
    readonly reason: string,
  ) {
    super();
  }
}

export interface StockShippingEvent {
  sku: string;
  quantity: number;
}

export class OrderPlacedEventHandler {
  handle(event: OrderPlacedEvent): string {
    return `placed: ${event.orderId}`;
  }
}
