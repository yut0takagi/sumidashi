import { Money } from "./money";
import {
  MEMBER_DISCOUNT_RATE,
  CAMPAIGN_DISCOUNT_RATE,
} from "../application/pricing-settings";

export class DiscountPolicy {
  apply(price: Money, isMember: boolean): Money {
    const rate = isMember ? MEMBER_DISCOUNT_RATE : CAMPAIGN_DISCOUNT_RATE;
    return price.multiply(1 - rate);
  }
}
