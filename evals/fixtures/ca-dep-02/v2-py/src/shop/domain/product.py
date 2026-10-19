from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column

from shop.domain.base import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(primary_key=True)
    price: Mapped[Decimal]

    def reprice(self, rate: Decimal, session: Session) -> None:
        self.price = self.price * rate
        session.flush()
