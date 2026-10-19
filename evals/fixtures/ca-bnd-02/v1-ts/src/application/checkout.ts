import type { Request, Response } from "express";
import { CartRepository } from "../domain/cart-repository";

export class CheckoutUseCase {
  constructor(private readonly carts: CartRepository) {}

  async execute(req: Request, res: Response): Promise<void> {
    const cart = await this.carts.findById(this.cartIdOf(req));
    res.status(201).json({ cartId: cart.id, total: cart.total() });
  }

  private cartIdOf(req: Request): string {
    return String(req.params.cartId);
  }
}

export async function previewCheckout(
  carts: CartRepository,
  req: Request,
): Promise<number> {
  const cart = await carts.findById(String(req.query.cartId));
  return cart.total();
}
