import { Subscription } from "../domain/subscription";

export function renew(now: Date): Subscription {
  return Subscription.start(now);
}
