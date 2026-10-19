import { z } from "zod";

const schema = z.string().email().max(254);

export class EmailAddress {
  private constructor(readonly value: string) {}

  static of(raw: string): EmailAddress {
    return new EmailAddress(schema.parse(raw));
  }
}
