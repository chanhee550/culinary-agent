"""Storage backend selector.

STORAGE_BACKEND=sqlite (default) → db.repository (로컬 SQLite, 단일 사용자)
STORAGE_BACKEND=firestore        → db.firestore_repo (Firebase 멀티 사용자)

페이지/앱 코드는 항상 `from db.storage import ...` 만 사용합니다.
"""
import os

_BACKEND = os.getenv("STORAGE_BACKEND", "sqlite").lower()

if _BACKEND == "firestore":
    from db.firestore_repo import (
        init_db,
        get_all_ingredients,
        get_ingredient_names,
        add_ingredient,
        update_ingredient,
        delete_ingredient,
        upsert_ingredients,
        clear_all,
    )
else:
    from db.database import init_db
    from db.repository import (
        get_all_ingredients,
        get_ingredient_names,
        add_ingredient,
        update_ingredient,
        delete_ingredient,
        upsert_ingredients,
        clear_all,
    )

__all__ = [
    "init_db",
    "get_all_ingredients",
    "get_ingredient_names",
    "add_ingredient",
    "update_ingredient",
    "delete_ingredient",
    "upsert_ingredients",
    "clear_all",
]
