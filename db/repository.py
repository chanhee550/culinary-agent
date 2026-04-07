from db.database import get_connection
from db.models import Ingredient


def _row_to_ingredient(row) -> Ingredient:
    return Ingredient(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        quantity=row["quantity"],
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


def add_ingredient(name: str, category: str = "기타", quantity: str | None = None, source: str = "manual") -> Ingredient:
    conn = get_connection()
    conn.execute(
        """INSERT INTO ingredients (name, category, quantity, source)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
               quantity = COALESCE(excluded.quantity, ingredients.quantity),
               category = excluded.category,
               source = excluded.source""",
        (name, category, quantity, source),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ingredients WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_ingredient(row)


def update_ingredient(ingredient_id: int, name: str | None = None, category: str | None = None, quantity: str | None = None):
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
    """Bulk upsert from scan results. items: [{"name": str, "category": str}]"""
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


def clear_all():
    conn = get_connection()
    conn.execute("DELETE FROM ingredients")
    conn.commit()
    conn.close()
