from flask import Blueprint, request

from payments.application.refund import handle_refund
from payments.infrastructure.store import payment_store

bp = Blueprint("payments", __name__)


@bp.post("/refunds")
def refund():
    return handle_refund(request, payment_store)
