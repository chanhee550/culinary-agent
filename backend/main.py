"""O'CHEF — Mobile API.

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

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

load_dotenv()

import json  # noqa: E402

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
from db.repository import (  # noqa: E402  (master 풀기능, storage 추상화 X)
    add_missing_to_shopping,
    add_shopping_item,
    clear_checked_shopping,
    delete_saved_recipe,
    delete_shopping_item,
    get_saved_recipes,
    get_shopping_list,
    save_recipe,
    toggle_shopping_item,
    update_recipe_rating,
)
from services.recipe import recommend_recipes  # noqa: E402
from services.speech import parse_cooking_command, synthesize_reply, transcribe_audio  # noqa: E402
from services.vision import analyze_multiple_images  # noqa: E402
from services.voice_intent import claude_route  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="O'CHEF API", version="0.1.0", lifespan=lifespan)

# CORS — 모바일 PWA·로컬 dev 모두 허용. 프로덕션에선 도메인 화이트리스트로 좁히세요.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(anthropic.AuthenticationError)
async def anthropic_auth_handler(request: Request, exc: anthropic.AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={
            "error": "anthropic_auth_failed",
            "message": ".env 파일의 ANTHROPIC_API_KEY가 유효하지 않습니다. "
                       "console.anthropic.com/settings/keys 에서 새 키를 발급받아 갱신하세요.",
            "detail": str(exc),
        },
    )


@app.exception_handler(anthropic.APIError)
async def anthropic_api_handler(request: Request, exc: anthropic.APIError):
    return JSONResponse(
        status_code=502,
        content={
            "error": "anthropic_api_error",
            "message": "Claude API 호출에 실패했습니다.",
            "detail": str(exc),
        },
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


class VoiceCommandOut(BaseModel):
    text: str
    command: dict


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200)


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


# ---------- Voice Cooking Guide ----------

@app.post("/voice/command", response_model=VoiceCommandOut)
async def voice_command(
    file: UploadFile = File(...),
    recipe_context: str | None = Form(default=None),
):
    """Short voice command → transcription → cooking guide action.

    Claude 라우터를 먼저 시도하고, 실패 시 regex parser 로 fallback 합니다.
    recipe_context (JSON 문자열) 가 주어지면 자유 질문에 답할 수 있습니다.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="오디오 파일이 필요합니다.")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="오디오 파일은 25MB 이하여야 합니다.")

    filename = file.filename or "command.webm"
    text = transcribe_audio(content, filename=filename)

    ctx: dict | None = None
    if recipe_context:
        try:
            parsed = json.loads(recipe_context)
            if isinstance(parsed, dict):
                ctx = parsed
        except json.JSONDecodeError:
            ctx = None

    command = claude_route(text, ctx) or parse_cooking_command(text)
    return VoiceCommandOut(text=text, command=command)


@app.post("/voice/tts")
async def voice_tts(req: TTSRequest):
    """Short confirmation text → mp3 audio via edge-tts."""
    audio = await synthesize_reply(req.text)
    if not audio:
        raise HTTPException(status_code=502, detail="TTS 음성 생성에 실패했습니다.")
    return Response(content=audio, media_type="audio/mpeg")


# ---------- Saved Recipes ----------

class RecipeIn(BaseModel):
    name: str
    description: str = ""
    ingredients: list[str] = []
    missing: list[str] = []
    instructions: list[str] = []
    difficulty: str = "보통"
    time: str = ""
    substitutions: dict[str, str] = {}


class SavedRecipeOut(BaseModel):
    id: int
    name: str
    description: str
    ingredients: list[str]
    missing: list[str]
    instructions: list[str]
    difficulty: str
    time: str
    substitutions: dict
    rating: int | None
    saved_at: str


def _parse_saved(row) -> SavedRecipeOut:
    def _j(s, default):
        try:
            return json.loads(s) if s else default
        except (json.JSONDecodeError, TypeError):
            return default

    return SavedRecipeOut(
        id=row.id,
        name=row.name,
        description=row.description or "",
        ingredients=_j(row.ingredients, []),
        missing=_j(row.missing, []),
        instructions=_j(row.instructions, []),
        difficulty=row.difficulty or "보통",
        time=row.time or "",
        substitutions=_j(row.substitutions, {}),
        rating=row.rating,
        saved_at=row.saved_at,
    )


@app.get("/saved_recipes", response_model=list[SavedRecipeOut])
def list_saved_recipes():
    return [_parse_saved(r) for r in get_saved_recipes()]


@app.post("/saved_recipes")
def create_saved_recipe(recipe: RecipeIn):
    rid = save_recipe(recipe.model_dump())
    return {"id": rid}


class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


@app.patch("/saved_recipes/{recipe_id}/rating")
def patch_rating(recipe_id: int, body: RatingUpdate):
    update_recipe_rating(recipe_id, body.rating)
    return {"updated": recipe_id, "rating": body.rating}


@app.delete("/saved_recipes/{recipe_id}")
def remove_saved_recipe(recipe_id: int):
    delete_saved_recipe(recipe_id)
    return {"deleted": recipe_id}


# ---------- Shopping List ----------

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


@app.get("/shopping", response_model=list[ShoppingItemOut])
def list_shopping():
    items = get_shopping_list()
    return [
        ShoppingItemOut(
            id=i.id, name=i.name, quantity=i.quantity,
            category=i.category, checked=i.checked, added_at=i.added_at,
        )
        for i in items
    ]


@app.post("/shopping")
def create_shopping(item: ShoppingItemIn):
    add_shopping_item(item.name, item.quantity, item.category)
    return {"added": item.name}


@app.patch("/shopping/{item_id}/toggle")
def toggle_shopping(item_id: int):
    toggle_shopping_item(item_id)
    return {"toggled": item_id}


@app.delete("/shopping/{item_id}")
def remove_shopping(item_id: int):
    delete_shopping_item(item_id)
    return {"deleted": item_id}


@app.delete("/shopping/checked/all")
def clear_checked():
    clear_checked_shopping()
    return {"cleared": True}


class MissingItems(BaseModel):
    items: list[str]


@app.post("/shopping/from_missing")
def shopping_from_missing(body: MissingItems):
    """레시피의 부족 재료 목록 → 장보기 목록에 일괄 추가."""
    add_missing_to_shopping(body.items)
    return {"added": len(body.items)}
