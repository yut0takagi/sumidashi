export class PriceDto {
  amount = 0;
  currency = "JPY";

  equals(other: PriceDto): boolean {
    return this.amount === other.amount && this.currency === other.currency;
  }
}
