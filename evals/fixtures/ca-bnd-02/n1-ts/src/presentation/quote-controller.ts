import type { Request, Response } from "express";
import { QuoteShipping } from "../application/quote-shipping";

export class QuoteController {
  constructor(private readonly quoteShipping: QuoteShipping) {}

  handle(req: Request, res: Response): void {
    const result = this.quoteShipping.execute({
      region: String(req.query.region),
      weightKg: Number(req.query.weightKg),
    });
    res.json(result);
  }
}
