"""장보기 목록 CRUD + 부족 재료 일괄 추가."""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.auth import CurrentUser
from db.repository import (
    add_missing_to_shopping,
    add_shopping_item,
    clear_checked_shopping,
    delete_shopping_item,
    get_shopping_list,
    toggle_shopping_item,
)

router = APIRouter(prefix="/shopping", tags=["shopping"])


# ---------- Schemas ----------

class ShoppingItemIn(BaseModel):
    name: str
    quantity: str | None = None
    category: str = "기타"


class ShoppingItemOut(BaseModel):
    id: int
    name: str
    quantity: str | None
    category: str
    checked: bool
    added_at: str


class MissingItems(BaseModel):
    items: list[str]


# ---------- Endpoints ----------

@router.get("", response_model=list[ShoppingItemOut])
def list_shopping(user: CurrentUser):
    items = get_shopping_list(user_id=user.id)
    return [
        ShoppingItemOut(
            id=i.id, name=i.name, quantity=i.quantity,
            category=i.category, checked=i.checked, added_at=i.added_at,
        )
        for i in items
    ]


@router.post("")
def create_shopping(item: ShoppingItemIn, user: CurrentUser):
    add_shopping_item(item.name, item.quantity, item.category, user_id=user.id)
    return {"added": item.name}


@router.patch("/{item_id}/toggle")
def toggle_shopping(item_id: int, user: CurrentUser):
    toggle_shopping_item(item_id, user_id=user.id)
    return {"toggled": item_id}


@router.delete("/{item_id}")
def remove_shopping(item_id: int, user: CurrentUser):
    delete_shopping_item(item_id, user_id=user.id)
    return {"deleted": item_id}


@router.delete("/checked/all")
def clear_checked(user: CurrentUser):
    clear_checked_shopping(user_id=user.id)
    return {"cleared": True}


@router.post("/from_missing")
def shopping_from_missing(body: MissingItems, user: CurrentUser):
    """레시피의 부족 재료 목록 → 장보기 목록에 일괄 추가."""
    add_missing_to_shopping(body.items, user_id=user.id)
    return {"added": len(body.items)}
