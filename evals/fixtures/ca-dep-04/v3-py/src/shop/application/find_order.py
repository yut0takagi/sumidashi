from shop.domain.order import Order


def find_order(orders: dict[str, Order], order_id: str) -> Order:
    return orders[order_id]
