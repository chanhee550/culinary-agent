import os

import streamlit as st
from db.database import init_db
from db.repository import get_ingredient_names
from services.recipe import recommend_recipes

init_db()

st.header("레시피 추천")

# API 키 확인
if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_api_key_here":
    st.warning("`.env` 파일에 `ANTHROPIC_API_KEY`를 설정해주세요.")
    st.stop()

# 현재 재료 불러오기
ingredient_names = get_ingredient_names()

if not ingredient_names:
    st.info("등록된 재료가 없습니다. '재료 관리' 또는 '냉장고 스캔' 페이지에서 재료를 추가해주세요.")
    st.stop()

# 재료 요약
st.subheader("보유 재료")
st.markdown(", ".join(f"`{name}`" for name in ingredient_names))

# 추천 옵션
col1, col2 = st.columns(2)
with col1:
    max_missing = st.slider("허용할 부족 재료 수", min_value=0, max_value=5, value=2)
with col2:
    st.metric("보유 재료 수", f"{len(ingredient_names)}개")

# 추천 버튼
if st.button("레시피 추천받기", type="primary", use_container_width=True):
    with st.spinner("AI가 레시피를 찾고 있습니다..."):
        try:
            recipes = recommend_recipes(ingredient_names, max_missing=max_missing)
        except Exception as e:
            st.error(f"레시피 추천 중 오류가 발생했습니다: {e}")
            st.stop()

    if not recipes:
        st.warning("추천할 레시피를 찾지 못했습니다. 재료를 더 추가해보세요.")
        st.stop()

    st.session_state["recipes"] = recipes

# 레시피 결과 표시
if "recipes" in st.session_state:
    recipes = st.session_state["recipes"]
    st.subheader(f"추천 레시피 ({len(recipes)}개)")

    difficulty_levels = ['쉬움', '보통', '어려움']
    for i, recipe in enumerate(recipes):
        diff = recipe.get('difficulty', '보통')
        stars = 3 - difficulty_levels.index(diff) if diff in difficulty_levels else 2
        with st.expander(
            f"{'⭐' * stars} **{recipe['name']}** — {recipe.get('description', '')} "
            f"({diff} · {recipe.get('time', '?')})",
            expanded=(i == 0),
        ):
            # 재료 표시 (색상 코딩)
            st.markdown("#### 재료")
            missing = set(recipe.get("missing", []))
            substitutions = recipe.get("substitutions", {})

            for ing in recipe.get("ingredients", []):
                if ing in missing and ing in substitutions:
                    st.markdown(f"- 🟡 ~~{ing}~~ → 대체 가능")
                elif ing in missing:
                    st.markdown(f"- 🔴 **{ing}** (부족)")
                else:
                    st.markdown(f"- 🟢 {ing}")

            # 대체 재료 안내
            if substitutions:
                st.markdown("#### 대체 재료")
                for orig, sub_text in substitutions.items():
                    st.markdown(f"- {sub_text}")

            # 조리법
            st.markdown("#### 조리법")
            for step in recipe.get("instructions", []):
                st.markdown(f"{step}")
