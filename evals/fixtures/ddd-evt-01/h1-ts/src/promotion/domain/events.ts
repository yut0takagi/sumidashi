export interface BaseEvent {
  occurredAt: Date;
}

export interface CouponIssued extends BaseEvent {
  couponCode: string;
}

export type CouponRedeemEvent = BaseEvent & {
  couponCode: string;
  orderId: string;
};

export interface GiftWrapEvent extends BaseEvent {
  orderId: string;
  message: string;
}
