from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine

from shop.domain.subscription import Plan, Subscription


def test_renew_extends_expiry():
    engine = create_engine("sqlite://")
    assert engine is not None
    sub = Subscription(Plan.MONTHLY, date(2026, 1, 1))
    sub.renew(Decimal("980"), today=date(2026, 1, 1))
    assert sub.expires_on == date(2026, 1, 31)
