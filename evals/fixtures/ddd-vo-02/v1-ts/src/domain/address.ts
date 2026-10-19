import { ValueObject } from "./value-object";

interface AddressProps {
  postalCode: string;
  prefecture: string;
}

export class Address extends ValueObject<AddressProps> {
  zipCode: string;

  constructor(props: AddressProps) {
    super(props);
    this.zipCode = props.postalCode;
  }

  changeZipCode(zipCode: string): void {
    this.zipCode = zipCode;
  }
}
