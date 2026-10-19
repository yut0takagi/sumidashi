from decimal import Decimal

from billing.domain.invoice import Invoice


def issue_invoice(invoice_id: str, amount: str) -> Invoice:
    return Invoice(invoice_id, Decimal(amount))
