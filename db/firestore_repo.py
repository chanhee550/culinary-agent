"""Firestore-backed repository.

Schema:
    /users/{user_id}/ingredients/{auto_id}
        name: string                    (UNIQUE within user)
        category: string                (default "기타")
        quantity: string | null
        source: string                  ("scan" | "manual")
        created_at: timestamp           (server time)
        updated_at: timestamp           (server time)

User scoping:
    user_id is read from FIREBASE_USER_ID (default "local"). When Firebase Auth
    is added later, replace this with the real uid.

Credentials:
    Either GOOGLE_APPLICATION_CREDENTIALS pointing to a service-account JSON,
    or FIREBASE_CREDENTIALS_PATH (alias). On managed environments, default
    application credentials are used automatically.
"""
import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

from db.models import Ingredient


def _user_id() -> str:
    return os.getenv("FIREBASE_USER_ID", "local")


@lru_cache(maxsize=1)
def _client():
    if not firebase_admin._apps:
        cred_path = (
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or os.getenv("FIREBASE_CREDENTIALS_PATH")
        )
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    return firestore.client()


def _ingredients_ref():
    return _client().collection("users").document(_user_id()).collection("ingredients")


def _doc_to_ingredient(doc) -> Ingredient:
    data = doc.to_dict() or {}
    added_at = data.get("created_at")
    return Ingredient(
        id=doc.id,
        name=data.get("name", ""),
        category=data.get("category", "기타"),
        quantity=data.get("quantity"),
        added_at=added_at.isoformat() if added_at else "",
        source=data.get("source", "manual"),
    )


def init_db() -> None:
    """Firestore는 스키마 사전 정의가 필요 없음. 클라이언트 초기화만."""
    _client()


def get_all_ingredients() -> list[Ingredient]:
    docs = _ingredients_ref().order_by("category").order_by("name").stream()
    return [_doc_to_ingredient(d) for d in docs]


def get_ingredient_names() -> list[str]:
    docs = _ingredients_ref().order_by("name").stream()
    return [d.to_dict().get("name", "") for d in docs if d.to_dict()]


def _find_by_name(name: str):
    query = _ingredients_ref().where(filter=FieldFilter("name", "==", name)).limit(1)
    return next(iter(query.stream()), None)


def add_ingredient(
    name: str,
    category: str = "기타",
    quantity: str | None = None,
    source: str = "manual",
) -> Ingredient:
    name = name.strip()
    existing = _find_by_name(name)
    now = firestore.SERVER_TIMESTAMP

    if existing:
        update_data = {
            "category": category,
            "source": source,
            "updated_at": now,
        }
        if quantity is not None:
            update_data["quantity"] = quantity
        existing.reference.update(update_data)
        return _doc_to_ingredient(existing.reference.get())

    doc_ref = _ingredients_ref().document()
    doc_ref.set({
        "name": name,
        "category": category,
        "quantity": quantity,
        "source": source,
        "created_at": now,
        "updated_at": now,
    })
    return _doc_to_ingredient(doc_ref.get())


def update_ingredient(
    ingredient_id: str,
    name: str | None = None,
    category: str | None = None,
    quantity: str | None = None,
) -> None:
    update_data: dict = {"updated_at": firestore.SERVER_TIMESTAMP}
    if name is not None:
        update_data["name"] = name.strip()
    if category is not None:
        update_data["category"] = category
    if quantity is not None:
        update_data["quantity"] = quantity
    if len(update_data) > 1:
        _ingredients_ref().document(str(ingredient_id)).update(update_data)


def delete_ingredient(ingredient_id: str) -> None:
    _ingredients_ref().document(str(ingredient_id)).delete()


def upsert_ingredients(items: list[dict], source: str = "scan") -> None:
    """Bulk upsert. items: [{"name", "category", "quantity"?}]"""
    batch = _client().batch()
    now = firestore.SERVER_TIMESTAMP

    for item in items:
        name = item["name"].strip()
        existing = _find_by_name(name)
        category = item.get("category", "기타")
        quantity = item.get("quantity")

        if existing:
            payload = {
                "category": category,
                "source": source,
                "updated_at": now,
            }
            if quantity is not None:
                payload["quantity"] = quantity
            batch.update(existing.reference, payload)
        else:
            new_ref = _ingredients_ref().document()
            batch.set(new_ref, {
                "name": name,
                "category": category,
                "quantity": quantity,
                "source": source,
                "created_at": now,
                "updated_at": now,
            })

    batch.commit()


def clear_all() -> None:
    docs = list(_ingredients_ref().stream())
    if not docs:
        return
    batch = _client().batch()
    for doc in docs:
        batch.delete(doc.reference)
    batch.commit()
