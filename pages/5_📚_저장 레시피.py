import json

import streamlit as st
from db.database import init_db
from db.repository import get_saved_recipes, delete_saved_recipe, update_recipe_rating
from styles import apply_global_styles

init_db()
apply_global_styles()

st.header("📚 저장된 레시피")
st.caption("저장한 레시피를 다시 확인하고 평가할 수 있습니다.")

saved = get_saved_recipes()

if not saved:
    st.info("저장된 레시피가 없습니다. '레시피 추천' 페이지에서 마음에 드는 레시피를 저장해보세요.")
    st.stop()

st.markdown(f"총 **{len(saved)}개** 레시피가 저장되어 있습니다.")

for recipe in saved:
    ingredients = json.loads(recipe.ingredients) if recipe.ingredients else []
    missing = json.loads(recipe.missing) if recipe.missing else []
    instructions = json.loads(recipe.instructions) if recipe.instructions else []
    substitutions = json.loads(recipe.substitutions) if recipe.substitutions else {}

    # 별점 표시
    rating_display = "⭐" * (recipe.rating or 0) + "☆" * (5 - (recipe.rating or 0))

    with st.expander(f"**{recipe.name}** — {recipe.description}  {rating_display}"):
        # 저장 날짜
        st.caption(f"저장일: {recipe.saved_at[:10] if recipe.saved_at else '-'}")

        # 난이도 & 시간
        st.markdown(f"""
        <div style="display:flex; gap:0.6rem; margin-bottom:1rem; font-family:'Noto Sans KR',sans-serif;">
            <span style="background:#f5f5f5; border-radius:20px; padding:0.3rem 0.8rem; font-size:0.82rem;">
                난이도: {recipe.difficulty}
            </span>
            <span style="background:#f5f5f5; border-radius:20px; padding:0.3rem 0.8rem; font-size:0.82rem;">
                ⏱ {recipe.time}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # 재료
        st.markdown("**재료**")
        missing_set = set(missing)
        for ing in ingredients:
            if ing in missing_set and ing in substitutions:
                st.markdown(f"- 🟡 ~~{ing}~~ → 대체 가능")
            elif ing in missing_set:
                st.markdown(f"- 🔴 **{ing}** (부족)")
            else:
                st.markdown(f"- 🟢 {ing}")

        # 대체 재료
        if substitutions:
            st.markdown("**대체 재료**")
            for orig, sub_text in substitutions.items():
                st.markdown(f"- {sub_text}")

        # 조리법
        st.markdown("**조리법**")
        for step in instructions:
            st.markdown(f"- {step}")

        st.markdown("---")

        # 별점 평가
        col_rating, col_del = st.columns([3, 1])
        with col_rating:
            new_rating = st.slider(
                "별점 평가", min_value=1, max_value=5,
                value=recipe.rating or 3,
                key=f"rating_{recipe.id}",
            )
            if st.button("평가 저장", key=f"rate_save_{recipe.id}", use_container_width=True):
                update_recipe_rating(recipe.id, new_rating)
                st.success("평가가 저장되었습니다!")
                st.rerun()
        with col_del:
            st.markdown("")
            if st.button("삭제", key=f"del_saved_{recipe.id}", use_container_width=True):
                delete_saved_recipe(recipe.id)
                st.rerun()
