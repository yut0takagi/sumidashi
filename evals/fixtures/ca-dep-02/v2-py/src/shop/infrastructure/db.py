from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql+psycopg://localhost/shop")
SessionLocal = sessionmaker(bind=engine)
