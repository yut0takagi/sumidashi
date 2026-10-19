import { Router } from "express";
import { CheckoutUseCase } from "../application/checkout";

export function checkoutRouter(useCase: CheckoutUseCase): Router {
  const router = Router();
  router.post("/carts/:cartId/checkout", (req, res) => useCase.execute(req, res));
  return router;
}
