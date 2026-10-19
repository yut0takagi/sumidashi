from decimal import Decimal

import requests

PRICE_FEED_URL = "https://prices.example.com"


def latest_price(sku: str) -> Decimal:
    response = requests.get(f"{PRICE_FEED_URL}/{sku}", timeout=5)
    return Decimal(str(response.json()["price"]))
