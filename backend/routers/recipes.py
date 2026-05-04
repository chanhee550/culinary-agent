"""레시피 추천 + 저장된 레시피 관리."""
import json

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.auth import CurrentUser
from db.repository import (
    delete_saved_recipe,
    get_ingredient_names,
    get_saved_recipes,
    save_recipe,
    update_recipe_rating,
)
from services.recipe import recommend_recipes

router = APIRouter(tags=["recipes"])


# ---------- Schemas ----------

class RecipeRequest(BaseModel):
    ingredients: list[str] | None = None
    max_missing: int = Field(default=2, ge=0, le=5)
    cuisine_filter: str = ""
    taste_filter: str = ""


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


class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


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


# ---------- Endpoints ----------

@router.post("/recipes")
def recipes(req: RecipeRequest, user: CurrentUser):
    """보유 재료 기반 레시피 추천. 프로필·맛/요리 필터를 services/recipe.py에 위임."""
    ingredients = req.ingredients or get_ingredient_names(user_id=user.id)
    if not ingredients:
        return []
    return recommend_recipes(
        ingredients,
        max_missing=req.max_missing,
        cuisine_filter=req.cuisine_filter,
        taste_filter=req.taste_filter,
        user_id=user.id,
    )


@router.get("/saved_recipes", response_model=list[SavedRecipeOut])
def list_saved_recipes(user: CurrentUser):
    return [_parse_saved(r) for r in get_saved_recipes(user_id=user.id)]


@router.post("/saved_recipes")
def create_saved_recipe(recipe: RecipeIn, user: CurrentUser):
    rid = save_recipe(recipe.model_dump(), user_id=user.id)
    return {"id": rid}


@router.patch("/saved_recipes/{recipe_id}/rating")
def patch_rating(recipe_id: int, body: RatingUpdate, user: CurrentUser):
    update_recipe_rating(recipe_id, body.rating, user_id=user.id)
    return {"updated": recipe_id, "rating": body.rating}


@router.delete("/saved_recipes/{recipe_id}")
def remove_saved_recipe(recipe_id: int, user: CurrentUser):
    delete_saved_recipe(recipe_id, user_id=user.id)
    return {"deleted": recipe_id}
