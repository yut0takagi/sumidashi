import { DomainEvent } from "./domain-event";
import { OrderPlaced } from "./order-events";

export interface OrderPlacedHandler {
  handle(event: OrderPlaced): Promise<void>;
}

export class EventBus {
  private readonly queue: DomainEvent[] = [];

  publish(event: DomainEvent): void {
    this.queue.push(event);
  }
}
