from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shop.infrastructure.repositories import ProductRepository

engine = create_engine("sqlite:///shop.db")
SessionLocal = sessionmaker(bind=engine)


def product_repository() -> ProductRepository:
    return ProductRepository(SessionLocal())
