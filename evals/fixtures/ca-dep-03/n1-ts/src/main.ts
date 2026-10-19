import Stripe from "stripe";
import { PayInvoice } from "./application/pay-invoice";
import { StripePaymentGateway } from "./infrastructure/stripe-payment-gateway";
import { InvoiceController } from "./presentation/invoice-controller";

const gateway = new StripePaymentGateway(new Stripe(process.env.STRIPE_KEY ?? ""));
export const controller = new InvoiceController(new PayInvoice(gateway));
