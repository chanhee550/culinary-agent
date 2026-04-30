"""Culinary Agent — Mobile API.

기존 services/, db/ 모듈을 그대로 재사용하여 모바일 앱(PWA/TWA)이 호출할 수 있는
HTTP 엔드포인트를 노출합니다. Streamlit 앱과 SQLite를 공유합니다.

실행:
    cd culinary-agent
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

배포(Railway/Cloud Run):
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from db.storage import (  # noqa: E402
    add_ingredient,
    clear_all,
    delete_ingredient,
    get_all_ingredients,
    get_ingredient_names,
    init_db,
    update_ingredient,
    upsert_ingredients,
)
from services.recipe import recommend_recipes  # noqa: E402
from services.vision import analyze_multiple_images  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Culinary Agent API", version="0.1.0", lifespan=lifespan)

# CORS — 모바일 PWA·로컬 dev 모두 허용. 프로덕션에선 도메인 화이트리스트로 좁히세요.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class RecipeRequest(BaseModel):
    ingredients: list[str] | None = None
    max_missing: int = Field(default=2, ge=0, le=5)
    cuisine_filter: str = ""
    taste_filter: str = ""


# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


@app.post("/scan")
async def scan(files: list[UploadFile] = File(...)):
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


@app.get("/ingredients", response_model=list[IngredientOut])
def list_ingredients():
    items = get_all_ingredients()
    return [
        IngredientOut(
            id=i.id, name=i.name, category=i.category,
            quantity=i.quantity,
            expiry_date=getattr(i, "expiry_date", None),
            source=i.source,
        )
        for i in items
    ]


@app.post("/ingredients", response_model=IngredientOut)
def create_ingredient(item: IngredientIn):
    result = add_ingredient(
        item.name, item.category, item.quantity,
        expiry_date=item.expiry_date, source="manual",
    )
    return IngredientOut(
        id=result.id, name=result.name, category=result.category,
        quantity=result.quantity,
        expiry_date=getattr(result, "expiry_date", None),
        source=result.source,
    )


@app.post("/ingredients/bulk")
def bulk_create(payload: BulkIngredientsIn):
    items = [i.model_dump() for i in payload.items]
    upsert_ingredients(items, source=payload.source)
    return {"saved": len(items)}


@app.patch("/ingredients/{ingredient_id}")
def patch_ingredient(ingredient_id: int, body: IngredientUpdate):
    update_ingredient(
        ingredient_id,
        name=body.name,
        category=body.category,
        quantity=body.quantity,
        expiry_date=body.expiry_date,
    )
    return {"updated": ingredient_id}


@app.delete("/ingredients/{ingredient_id}")
def remove_ingredient(ingredient_id: int):
    delete_ingredient(ingredient_id)
    return {"deleted": ingredient_id}


@app.delete("/ingredients")
def remove_all():
    clear_all()
    return {"cleared": True}


@app.post("/recipes")
def recipes(req: RecipeRequest):
    """보유 재료 기반 레시피 추천. 프로필·맛/요리 필터를 master 쪽 services/recipe.py에 위임."""
    ingredients = req.ingredients or get_ingredient_names()
    if not ingredients:
        return []
    return recommend_recipes(
        ingredients,
        max_missing=req.max_missing,
        cuisine_filter=req.cuisine_filter,
        taste_filter=req.taste_filter,
    )
