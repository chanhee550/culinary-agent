from dataclasses import dataclass


@dataclass
class Ingredient:
    id: int | None
    name: str
    category: str
    quantity: str | None
    expiry_date: str | None
    added_at: str
    source: str  # "scan" | "manual"


@dataclass
class UserProfile:
    skill_level: str  # "초보" | "중급" | "고급"
    cuisine_preference: str  # comma-separated: "한식,양식"
    taste_preference: str  # comma-separated: "매운맛,단맛"
    allergies: str  # comma-separated: "우유,계란"


@dataclass
class SavedRecipe:
    id: int | None
    name: str
    description: str
    ingredients: str  # JSON string
    missing: str  # JSON string
    instructions: str  # JSON string
    difficulty: str
    time: str
    substitutions: str  # JSON string
    rating: int | None
    saved_at: str


@dataclass
class ShoppingItem:
    id: int | None
    name: str
    quantity: str | None
    category: str
    checked: bool
    added_at: str
