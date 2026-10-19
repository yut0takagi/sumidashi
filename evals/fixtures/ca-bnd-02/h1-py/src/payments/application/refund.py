from decimal import Decimal

from flask import Request, Response, jsonify

from payments.domain.repository import PaymentRepository


def handle_refund(req: Request, payments: PaymentRepository) -> Response:
    body = req.get_json()
    payment = payments.get(body["payment_id"])
    payment.refund(_amount_of(body))
    payments.save(payment)
    return jsonify({"status": "refunded"})


def _amount_of(body: dict) -> Decimal:
    return Decimal(str(body["amount"]))
