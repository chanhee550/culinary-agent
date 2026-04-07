from dataclasses import dataclass


@dataclass
class Ingredient:
    id: int | None
    name: str
    category: str
    quantity: str | None
    added_at: str
    source: str  # "scan" | "manual"
