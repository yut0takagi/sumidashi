from fastapi import APIRouter

from shop.application.find_order import find_order
from shop.infrastructure.container import container

router = APIRouter()


@router.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    order = find_order(container.orders, order_id)
    return {"id": order.id}
