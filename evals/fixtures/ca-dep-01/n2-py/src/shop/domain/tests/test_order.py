from shop.domain.order import Order
from shop.infrastructure.sql_order_repository import SqlOrderRepository


def test_new_order_has_zero_total():
    assert Order().total() == 0


def test_repository_round_trip(session):
    repo = SqlOrderRepository(session)
    order = Order()
    repo.add(order)
    assert repo.get(order.id) is order
