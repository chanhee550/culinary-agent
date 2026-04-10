import json

from db.database import get_connection
from db.models import Ingredient, UserProfile, SavedRecipe, ShoppingItem


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


def get_all_ingredients() -> list[Ingredient]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ingredients ORDER BY category, name"
    ).fetchall()
    conn.close()
    return [_row_to_ingredient(r) for r in rows]


def add_ingredient(name: str, category: str = "기타", quantity: str | None = None,
                   expiry_date: str | None = None, source: str = "manual") -> Ingredient:
    conn = get_connection()
    conn.execute(
        """INSERT INTO ingredients (name, category, quantity, expiry_date, source)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
               quantity = COALESCE(excluded.quantity, ingredients.quantity),
               category = excluded.category,
               expiry_date = COALESCE(excluded.expiry_date, ingredients.expiry_date),
               source = excluded.source""",
        (name, category, quantity, expiry_date, source),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ingredients WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_ingredient(row)


def update_ingredient(ingredient_id: int, name: str | None = None, category: str | None = None,
                      quantity: str | None = None, expiry_date: str | None = None):
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
        values.append(ingredient_id)
        conn.execute(f"UPDATE ingredients SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()


def delete_ingredient(ingredient_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    conn.commit()
    conn.close()


def upsert_ingredients(items: list[dict], source: str = "scan"):
    conn = get_connection()
    for item in items:
        conn.execute(
            """INSERT INTO ingredients (name, category, source)
               VALUES (?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   category = excluded.category""",
            (item["name"], item.get("category", "기타"), source),
        )
    conn.commit()
    conn.close()


def get_ingredient_names() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT name FROM ingredients ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def get_expiring_ingredients(days: int = 3) -> list[Ingredient]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM ingredients
           WHERE expiry_date IS NOT NULL
             AND expiry_date != ''
             AND date(expiry_date) <= date('now', '+' || ? || ' days')
           ORDER BY expiry_date ASC""",
        (days,),
    ).fetchall()
    conn.close()
    return [_row_to_ingredient(r) for r in rows]


def clear_all():
    conn = get_connection()
    conn.execute("DELETE FROM ingredients")
    conn.commit()
    conn.close()


# ===== User Profile =====

def get_profile() -> UserProfile:
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
    conn.close()
    return UserProfile(
        skill_level=row["skill_level"],
        cuisine_preference=row["cuisine_preference"],
        taste_preference=row["taste_preference"],
        allergies=row["allergies"],
    )


def update_profile(skill_level: str, cuisine_preference: str,
                   taste_preference: str, allergies: str):
    conn = get_connection()
    conn.execute(
        """UPDATE user_profile SET
               skill_level = ?, cuisine_preference = ?,
               taste_preference = ?, allergies = ?
           WHERE id = 1""",
        (skill_level, cuisine_preference, taste_preference, allergies),
    )
    conn.commit()
    conn.close()


# ===== Saved Recipes =====

def save_recipe(recipe: dict) -> int:
    conn = get_connection()
    conn.execute(
        """INSERT INTO saved_recipes (name, description, ingredients, missing,
               instructions, difficulty, time, substitutions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
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


def get_saved_recipes() -> list[SavedRecipe]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM saved_recipes ORDER BY saved_at DESC").fetchall()
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


def update_recipe_rating(recipe_id: int, rating: int):
    conn = get_connection()
    conn.execute("UPDATE saved_recipes SET rating = ? WHERE id = ?", (rating, recipe_id))
    conn.commit()
    conn.close()


def delete_saved_recipe(recipe_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM saved_recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()


# ===== Shopping List =====

def add_shopping_item(name: str, quantity: str | None = None, category: str = "기타"):
    conn = get_connection()
    conn.execute(
        """INSERT INTO shopping_list (name, quantity, category)
           VALUES (?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
               quantity = excluded.quantity,
               category = excluded.category""",
        (name, quantity, category),
    )
    conn.commit()
    conn.close()


def get_shopping_list() -> list[ShoppingItem]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM shopping_list ORDER BY checked, category, name").fetchall()
    conn.close()
    return [
        ShoppingItem(
            id=r["id"], name=r["name"], quantity=r["quantity"],
            category=r["category"], checked=bool(r["checked"]),
            added_at=r["added_at"],
        )
        for r in rows
    ]


def toggle_shopping_item(item_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE shopping_list SET checked = NOT checked WHERE id = ?", (item_id,)
    )
    conn.commit()
    conn.close()


def delete_shopping_item(item_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM shopping_list WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def clear_checked_shopping():
    conn = get_connection()
    conn.execute("DELETE FROM shopping_list WHERE checked = 1")
    conn.commit()
    conn.close()


def add_missing_to_shopping(missing_items: list[str]):
    conn = get_connection()
    for name in missing_items:
        conn.execute(
            """INSERT INTO shopping_list (name)
               VALUES (?)
               ON CONFLICT(name) DO NOTHING""",
            (name,),
        )
    conn.commit()
    conn.close()
