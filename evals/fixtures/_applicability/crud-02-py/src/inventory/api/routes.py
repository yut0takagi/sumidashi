from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from inventory.db import crud
from inventory.db.session import get_session

router = APIRouter(prefix="/items")


class ItemIn(BaseModel):
    name: str
    quantity: int = 0


@router.get("/")
def list_items(session: Session = Depends(get_session)):
    return crud.list_items(session)


@router.post("/", status_code=201)
def create_item(body: ItemIn, session: Session = Depends(get_session)):
    return crud.create_item(session, body.name, body.quantity)


@router.patch("/{item_id}")
def update_quantity(item_id: int, quantity: int, session: Session = Depends(get_session)):
    item = crud.update_quantity(session, item_id, quantity)
    if item is None:
        raise HTTPException(status_code=404)
    return item
