"""재료 CRUD + 비전 스캔 엔드포인트."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.auth import CurrentUser
from db.repository import (
    add_ingredient,
    clear_all,
    delete_ingredient,
    get_all_ingredients,
    update_ingredient,
    upsert_ingredients,
)
from services.vision import analyze_multiple_images

router = APIRouter(tags=["ingredients"])


# ---------- Schemas ----------

class IngredientIn(BaseModel):
    name: str
    category: str = "기타"
    quantity: str | None = None
    expiry_date: str | None = None


class IngredientOut(BaseModel):
    id: int | str | None
    name: str
    category: str
    quantity: str | None
    expiry_date: str | None = None
    source: str


class IngredientUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    quantity: str | None = None
    expiry_date: str | None = None


class BulkIngredientsIn(BaseModel):
    items: list[IngredientIn]
    source: str = "scan"


# ---------- Endpoints ----------

@router.post("/scan")
async def scan(user: CurrentUser, files: list[UploadFile] = File(...)):
    """다중 이미지 업로드 → Level 2 결과 (confirmed + unknowns + errors)."""
    if not files:
        raise HTTPException(status_code=400, detail="이미지가 필요합니다.")

    images: list[tuple[bytes, str]] = []
    for f in files:
        content = await f.read()
        if not content:
            continue
        images.append((content, f.content_type or "image/jpeg"))

    if not images:
        raise HTTPException(status_code=400, detail="유효한 이미지가 없습니다.")

    return analyze_multiple_images(images)


@router.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients(user: CurrentUser):
    items = get_all_ingredients(user_id=user.id)
    return [
        IngredientOut(
            id=i.id, name=i.name, category=i.category,
            quantity=i.quantity,
            expiry_date=getattr(i, "expiry_date", None),
            source=i.source,
        )
        for i in items
    ]


@router.post("/ingredients", response_model=IngredientOut)
def create_ingredient(item: IngredientIn, user: CurrentUser):
    result = add_ingredient(
        item.name, item.category, item.quantity,
        expiry_date=item.expiry_date, source="manual",
        user_id=user.id,
    )
    return IngredientOut(
        id=result.id, name=result.name, category=result.category,
        quantity=result.quantity,
        expiry_date=getattr(result, "expiry_date", None),
        source=result.source,
    )


@router.post("/ingredients/bulk")
def bulk_create(payload: BulkIngredientsIn, user: CurrentUser):
    items = [i.model_dump() for i in payload.items]
    upsert_ingredients(items, source=payload.source, user_id=user.id)
    return {"saved": len(items)}


@router.patch("/ingredients/{ingredient_id}")
def patch_ingredient(ingredient_id: int, body: IngredientUpdate, user: CurrentUser):
    update_ingredient(
        ingredient_id,
        name=body.name,
        category=body.category,
        quantity=body.quantity,
        expiry_date=body.expiry_date,
        user_id=user.id,
    )
    return {"updated": ingredient_id}


@router.delete("/ingredients/{ingredient_id}")
def remove_ingredient(ingredient_id: int, user: CurrentUser):
    delete_ingredient(ingredient_id, user_id=user.id)
    return {"deleted": ingredient_id}


@router.delete("/ingredients")
def remove_all(user: CurrentUser):
    clear_all(user_id=user.id)
    return {"cleared": True}
