import axios from "axios";
import { Currency } from "./currency";

export class ExchangeRate {
  constructor(
    readonly from: Currency,
    readonly to: Currency,
    readonly rate: number,
  ) {}

  static async fetch(from: Currency, to: Currency): Promise<ExchangeRate> {
    const res = await axios.get(`https://rates.example.com/${from}/${to}`);
    return new ExchangeRate(from, to, res.data.rate);
  }
}
