import requests
from sqlalchemy.orm import Session


def charge(session: Session, subscription_id: str) -> None:
    requests.post(f"https://billing.example.com/charge/{subscription_id}", timeout=5)
    session.commit()
