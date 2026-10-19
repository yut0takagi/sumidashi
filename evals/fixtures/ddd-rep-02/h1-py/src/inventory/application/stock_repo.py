from typing import Protocol

import sqlalchemy as sa
from pymongo.collection import Collection

from inventory.domain.stock import Stock


class StockRepo(Protocol):
    def get(self, sku: str) -> Stock: ...

    def lock_rows(self, conn: sa.Connection, skus: list[str]) -> list[Stock]: ...

    def raw_collection(self) -> Collection: ...
