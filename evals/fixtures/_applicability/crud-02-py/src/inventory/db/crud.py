from sqlalchemy import select
from sqlalchemy.orm import Session

from inventory.db.models import Item


def list_items(session: Session) -> list[Item]:
    return list(session.scalars(select(Item).order_by(Item.id)))


def create_item(session: Session, name: str, quantity: int) -> Item:
    item = Item(name=name, quantity=quantity)
    session.add(item)
    session.commit()
    return item


def update_quantity(session: Session, item_id: int, quantity: int) -> Item | None:
    item = session.get(Item, item_id)
    if item is None:
        return None
    item.quantity = quantity
    session.commit()
    return item
