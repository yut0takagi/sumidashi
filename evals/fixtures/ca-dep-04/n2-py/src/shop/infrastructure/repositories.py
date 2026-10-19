from shop.domain.product import Product
from shop.infrastructure.db import SessionLocal


class ProductRepository:
    def __init__(self, session=None) -> None:
        self._session = session or SessionLocal()

    def get(self, sku: str) -> Product:
        return self._session.get(Product, sku)
