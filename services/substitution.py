import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "substitutions.json"

_cache: dict | None = None


def load_substitutions() -> dict:
    global _cache
    if _cache is None:
        with open(DATA_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def find_substitution(ingredient: str) -> dict | None:
    """특정 재료의 대체 레시피를 찾습니다."""
    subs = load_substitutions()
    return subs.get(ingredient)


def can_substitute(missing_ingredient: str, available: list[str]) -> bool:
    """부족한 재료를 보유 재료로 대체 가능한지 확인합니다."""
    sub = find_substitution(missing_ingredient)
    if sub is None:
        return False
    return all(comp in available for comp in sub.get("components", []))


def get_substitution_text(missing_ingredient: str, available: list[str]) -> str | None:
    """대체 가능한 경우 대체 방법 텍스트를 반환합니다."""
    sub = find_substitution(missing_ingredient)
    if sub is None:
        return None

    components = sub.get("components", [])
    need = [c for c in components if c not in available]

    if need:
        return None

    return f"**{missing_ingredient}** → {sub.get('ratio', '')} ({sub.get('note', '')})"


def find_all_substitutable(missing_list: list[str], available: list[str]) -> dict[str, str]:
    """부족 재료 목록 중 대체 가능한 것들을 찾아 대체법을 반환합니다."""
    result = {}
    for ingredient in missing_list:
        text = get_substitution_text(ingredient, available)
        if text:
            result[ingredient] = text
    return result
