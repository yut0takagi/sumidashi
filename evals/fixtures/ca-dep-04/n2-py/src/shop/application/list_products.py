from shop.domain.product import Product


def list_products(products: list[Product]) -> list[Product]:
    return sorted(products, key=lambda p: p._sku)
