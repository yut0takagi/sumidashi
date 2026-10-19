from fastapi import FastAPI

from shop.adapters.web import routes
from shop.domain.order import Order


class Container:
    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}

    def create_app(self) -> FastAPI:
        app = FastAPI()
        app.include_router(routes.router)
        return app


container = Container()
