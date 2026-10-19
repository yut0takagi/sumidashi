import { ShippingRate } from "../domain/shipping-rate";

export interface QuoteRequest {
  region: string;
  weightKg: number;
}

export interface QuoteResult {
  yen: number;
}

export class QuoteShipping {
  constructor(private readonly rates: ShippingRate[]) {}

  execute(request: QuoteRequest): QuoteResult {
    const rate = this.rates.find((r) => r.region === request.region);
    if (!rate) throw new Error(`no rate for ${request.region}`);
    return { yen: Math.ceil(rate.yenPerKg * request.weightKg) };
  }
}
