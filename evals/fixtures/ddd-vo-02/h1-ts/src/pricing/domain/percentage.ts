import { ValueObject } from "./value-object";

export class Percentage implements ValueObject<Percentage> {
  public label: string;
  private _rate: number;

  constructor(rate: number, label = "") {
    if (rate < 0 || rate > 100) throw new RangeError("rate must be between 0 and 100");
    this._rate = rate;
    this.label = label;
  }

  get rate(): number {
    return this._rate;
  }

  increment(): void {
    this._rate++;
  }

  add(delta: number): void {
    this._rate += delta;
  }

  equals(other: Percentage): boolean {
    return this._rate === other._rate;
  }
}
