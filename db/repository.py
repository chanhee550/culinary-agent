"""모든 도메인 데이터 접근 함수. user_id를 명시적으로 받습니다.

LEGACY_USER_ID(1)을 기본값으로 두어, 인증을 거치지 않는 호출(Streamlit, 단위 테스트)도
계속 동작하게 합니다. FastAPI 엔드포인트는 항상 인증된 사용자의 id를 명시적으로 넘깁니다.
"""
import json
from datetime import date

from db.database import get_connection, LEGACY_USER_ID
from db.models import Ingredient, UserProfile, SavedRecipe, ShoppingItem, DailyRecipes


# ===== Ingredients =====

def _row_to_ingredient(row) -> Ingredient:
    return Ingredient(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        quantity=row["quantity"],
        expiry_date=row["expiry_date"],
        added_at=row["added_at"],
        source=row["source"],
    )


def get_all_ingredients(user_id: int = LEGACY_USER_ID) -> list[Ingredient]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ingredients WHERE user_id = ? ORDER BY category, name",
        (user_id,),
    ).fetchall()
    conn.close()
    return [_row_to_ingredient(r) for r in rows]


def add_ingredient(name: str, category: str = "기타", quantity: str | None = None,
                   expiry_date: str | None = None, source: str = "manual",
                   user_id: int = LEGACY_USER_ID) -> Ingredient:
    conn = get_connection()
    conn.execute(
        """INSERT INTO ingredients (user_id, name, category, quantity, expiry_date, source)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, name) DO UPDATE SET
               quantity = COALESCE(excluded.quantity, ingredients.quantity),
               category = excluded.category,
               expiry_date = COALESCE(excluded.expiry_date, ingredients.expiry_date),
               source = excluded.source""",
        (user_id, name, category, quantity, expiry_date, source),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM ingredients WHERE user_id = ? AND name = ?",
        (user_id, name),
    ).fetchone()
    conn.close()
    return _row_to_ingredient(row)


def update_ingredient(ingredient_id: int, name: str | None = None, category: str | None = None,
                      quantity: str | None = None, expiry_date: str | None = None,
                      user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    fields, values = [], []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if quantity is not None:
        fields.append("quantity = ?")
        values.append(quantity)
    if expiry_date is not None:
        fields.append("expiry_date = ?")
        values.append(expiry_date)
    if fields:
        values.extend([ingredient_id, user_id])
        conn.execute(
            f"UPDATE ingredients SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
            values,
        )
        conn.commit()
    conn.close()


def delete_ingredient(ingredient_id: int, user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "DELETE FROM ingredients WHERE id = ? AND user_id = ?",
        (ingredient_id, user_id),
    )
    conn.commit()
    conn.close()


def upsert_ingredients(items: list[dict], source: str = "scan",
                       user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    for item in items:
        conn.execute(
            """INSERT INTO ingredients (user_id, name, category, quantity, expiry_date, source)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, name) DO UPDATE SET
                   category = excluded.category,
                   quantity = COALESCE(excluded.quantity, ingredients.quantity),
                   expiry_date = COALESCE(excluded.expiry_date, ingredients.expiry_date),
                   source = excluded.source""",
            (
                user_id,
                item["name"],
                item.get("category", "기타"),
                item.get("quantity"),
                item.get("expiry_date"),
                source,
            ),
        )
    conn.commit()
    conn.close()


def get_ingredient_names(user_id: int = LEGACY_USER_ID) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT name FROM ingredients WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["name"] for r in rows]


def get_expiring_ingredients(days: int = 3,
                             user_id: int = LEGACY_USER_ID) -> list[Ingredient]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM ingredients
           WHERE user_id = ?
             AND expiry_date IS NOT NULL
             AND expiry_date != ''
             AND date(expiry_date) <= date('now', '+' || ? || ' days')
           ORDER BY expiry_date ASC""",
        (user_id, days),
    ).fetchall()
    conn.close()
    return [_row_to_ingredient(r) for r in rows]


def clear_all(user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute("DELETE FROM ingredients WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ===== User Profile =====

def get_profile(user_id: int = LEGACY_USER_ID) -> UserProfile:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_profile WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        # 신규 사용자라면 즉시 기본 프로필 행을 만들고 반환
        conn.execute("INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM user_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    conn.close()
    return UserProfile(
        skill_level=row["skill_level"],
        cuisine_preference=row["cuisine_preference"],
        taste_preference=row["taste_preference"],
        allergies=row["allergies"],
    )


def update_profile(skill_level: str, cuisine_preference: str,
                   taste_preference: str, allergies: str,
                   user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO user_profile (user_id) VALUES (?)", (user_id,))
    conn.execute(
        """UPDATE user_profile SET
               skill_level = ?, cuisine_preference = ?,
               taste_preference = ?, allergies = ?
           WHERE user_id = ?""",
        (skill_level, cuisine_preference, taste_preference, allergies, user_id),
    )
    conn.commit()
    conn.close()


# ===== Saved Recipes =====

def save_recipe(recipe: dict, user_id: int = LEGACY_USER_ID) -> int:
    conn = get_connection()
    conn.execute(
        """INSERT INTO saved_recipes (user_id, name, description, ingredients, missing,
               instructions, difficulty, time, substitutions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            recipe.get("name", ""),
            recipe.get("description", ""),
            json.dumps(recipe.get("ingredients", []), ensure_ascii=False),
            json.dumps(recipe.get("missing", []), ensure_ascii=False),
            json.dumps(recipe.get("instructions", []), ensure_ascii=False),
            recipe.get("difficulty", "보통"),
            recipe.get("time", ""),
            json.dumps(recipe.get("substitutions", {}), ensure_ascii=False),
        ),
    )
    conn.commit()
    recipe_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return recipe_id


def get_saved_recipes(user_id: int = LEGACY_USER_ID) -> list[SavedRecipe]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM saved_recipes WHERE user_id = ? ORDER BY saved_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        SavedRecipe(
            id=r["id"], name=r["name"], description=r["description"],
            ingredients=r["ingredients"], missing=r["missing"],
            instructions=r["instructions"], difficulty=r["difficulty"],
            time=r["time"], substitutions=r["substitutions"],
            rating=r["rating"], saved_at=r["saved_at"],
        )
        for r in rows
    ]


def update_recipe_rating(recipe_id: int, rating: int, user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "UPDATE saved_recipes SET rating = ? WHERE id = ? AND user_id = ?",
        (rating, recipe_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_saved_recipe(recipe_id: int, user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "DELETE FROM saved_recipes WHERE id = ? AND user_id = ?",
        (recipe_id, user_id),
    )
    conn.commit()
    conn.close()


# ===== Shopping List =====

def add_shopping_item(name: str, quantity: str | None = None, category: str = "기타",
                      user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        """INSERT INTO shopping_list (user_id, name, quantity, category)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id, name) DO UPDATE SET
               quantity = excluded.quantity,
               category = excluded.category""",
        (user_id, name, quantity, category),
    )
    conn.commit()
    conn.close()


def get_shopping_list(user_id: int = LEGACY_USER_ID) -> list[ShoppingItem]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM shopping_list WHERE user_id = ? ORDER BY checked, category, name",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        ShoppingItem(
            id=r["id"], name=r["name"], quantity=r["quantity"],
            category=r["category"], checked=bool(r["checked"]),
            added_at=r["added_at"],
        )
        for r in rows
    ]


def toggle_shopping_item(item_id: int, user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "UPDATE shopping_list SET checked = NOT checked WHERE id = ? AND user_id = ?",
        (item_id, user_id),
    )
    conn.commit()
    conn.close()


def delete_shopping_item(item_id: int, user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "DELETE FROM shopping_list WHERE id = ? AND user_id = ?",
        (item_id, user_id),
    )
    conn.commit()
    conn.close()


def clear_checked_shopping(user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    conn.execute(
        "DELETE FROM shopping_list WHERE checked = 1 AND user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def add_missing_to_shopping(missing_items: list[str], user_id: int = LEGACY_USER_ID):
    conn = get_connection()
    for name in missing_items:
        conn.execute(
            """INSERT INTO shopping_list (user_id, name)
               VALUES (?, ?)
               ON CONFLICT(user_id, name) DO NOTHING""",
            (user_id, name),
        )
    conn.commit()
    conn.close()


# ===== Daily Recipes (오늘의 레시피) =====

def _today_iso() -> str:
    return date.today().isoformat()


def get_today_recipes(user_id: int = LEGACY_USER_ID) -> list[dict] | None:
    """오늘 날짜로 캐시된 레시피 반환. 없으면 None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT recipes_json FROM daily_recipes WHERE user_id = ? AND date = ?",
        (user_id, _today_iso()),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return json.loads(row["recipes_json"])
    except json.JSONDecodeError:
        return None


def save_today_recipes(recipes: list[dict], user_id: int = LEGACY_USER_ID) -> None:
    """오늘 날짜로 레시피 캐싱. 같은 날 재호출 시 덮어씀."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO daily_recipes (user_id, date, recipes_json, generated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id, date) DO UPDATE SET
               recipes_json = excluded.recipes_json,
               generated_at = CURRENT_TIMESTAMP""",
        (user_id, _today_iso(), json.dumps(recipes, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def clear_today_recipes(user_id: int = LEGACY_USER_ID) -> None:
    """오늘 캐시 강제 삭제 (사용자 '새로 받기' 동작)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM daily_recipes WHERE user_id = ? AND date = ?",
        (user_id, _today_iso()),
    )
    conn.commit()
    conn.close()


def prune_old_daily_recipes(keep_days: int = 7) -> None:
    """오래된 캐시 정리. keep_days 이전 데이터 삭제 (모든 사용자)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM daily_recipes WHERE date < date('now', '-' || ? || ' days')",
        (keep_days,),
    )
    conn.commit()
    conn.close()
