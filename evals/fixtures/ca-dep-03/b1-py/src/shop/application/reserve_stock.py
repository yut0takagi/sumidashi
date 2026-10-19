from __future__ import annotations

from typing import TYPE_CHECKING

from shop.domain.stock import Stock

if TYPE_CHECKING:
    from shop.infrastructure.db import UnitOfWork


def reserve_stock(uow: UnitOfWork, sku: str, quantity: int) -> Stock:
    with uow:
        stock = uow.stocks.get(sku)
        stock.reserve(quantity)
        uow.commit()
    return stock
