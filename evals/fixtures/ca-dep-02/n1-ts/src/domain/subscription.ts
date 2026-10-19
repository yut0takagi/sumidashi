import { addMonths, isAfter } from "date-fns";
import Decimal from "decimal.js";
import { v4 as uuid } from "uuid";
import { sortBy } from "lodash";

export class Subscription {
  private readonly payments: { paidAt: Date; amount: Decimal }[] = [];

  private constructor(
    readonly id: string,
    private expiresAt: Date,
  ) {}

  static start(now: Date): Subscription {
    return new Subscription(uuid(), addMonths(now, 1));
  }

  isActive(now: Date): boolean {
    return isAfter(this.expiresAt, now);
  }

  latestPayment(): { paidAt: Date; amount: Decimal } | undefined {
    return sortBy(this.payments, (p) => p.paidAt.getTime()).at(-1);
  }
}
