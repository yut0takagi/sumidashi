import { IsPostalCode, Length } from "class-validator";

export class ShippingAddress {
  @IsPostalCode("JP")
  readonly postalCode: string;

  @Length(1, 120)
  readonly line1: string;

  constructor(postalCode: string, line1: string) {
    this.postalCode = postalCode;
    this.line1 = line1;
  }
}
