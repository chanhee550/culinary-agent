import os

import streamlit as st
from db.database import init_db
from db.repository import (
    get_ingredient_names, get_profile, get_saved_recipes,
    save_recipe, add_missing_to_shopping,
)
from services.recipe import recommend_recipes
from styles import apply_global_styles

init_db()
apply_global_styles()

st.header("🍽️ 레시피 추천")

# API 키 확인
if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_api_key_here":
    st.warning("`.env` 파일에 `ANTHROPIC_API_KEY`를 설정해주세요.")
    st.stop()

# 현재 재료 불러오기
ingredient_names = get_ingredient_names()

if not ingredient_names:
    st.info("등록된 재료가 없습니다. '재료 관리' 또는 '냉장고 스캔' 페이지에서 재료를 추가해주세요.")
    st.stop()

# 재료 요약 - 태그 스타일
tags_html = " ".join(
    f'<span style="display:inline-block; background:#f0f0f0; border-radius:20px; '
    f'padding:0.3rem 0.8rem; margin:0.2rem; font-size:0.85rem;">{name}</span>'
    for name in ingredient_names
)
st.markdown(f"""
<div style="margin-bottom:1rem; font-family:'Noto Sans KR',sans-serif;">
    <div style="font-weight:600; margin-bottom:0.5rem;">보유 재료 ({len(ingredient_names)}개)</div>
    <div>{tags_html}</div>
</div>
""", unsafe_allow_html=True)

# 프로필 정보 로드
profile = get_profile()

# 추천 옵션
st.subheader("추천 옵션")
col1, col2 = st.columns(2)
with col1:
    max_missing = st.slider("허용할 부족 재료 수", min_value=0, max_value=5, value=2)
with col2:
    st.metric("보유 재료 수", f"{len(ingredient_names)}개")

# 선호도 필터 (프로필 기본값 사용, 임시 변경 가능)
with st.expander("선호도 필터 (프로필 기본값 적용중)"):
    cuisine_filter = st.text_input(
        "요리 종류 (쉼표 구분)",
        value=profile.cuisine_preference,
        placeholder="예: 한식, 양식",
    )
    taste_filter = st.text_input(
        "맛 선호 (쉼표 구분)",
        value=profile.taste_preference,
        placeholder="예: 매운맛, 감칠맛",
    )
    if profile.allergies:
        st.caption(f"⚠️ 알레르기 제외 재료: {profile.allergies}")

# 추천 버튼
if st.button("레시피 추천받기", type="primary", use_container_width=True):
    with st.spinner("AI가 레시피를 찾고 있습니다..."):
        try:
            recipes = recommend_recipes(
                ingredient_names, max_missing=max_missing,
                cuisine_filter=cuisine_filter, taste_filter=taste_filter,
            )
        except Exception as e:
            st.error(f"레시피 추천 중 오류가 발생했습니다: {e}")
            # API 실패 대체 UX
            saved = get_saved_recipes()
            if saved:
                st.info("이전에 저장한 레시피를 확인해보세요!")
                for sr in saved[:3]:
                    st.markdown(f"- **{sr.name}** — {sr.description}")
            else:
                st.info("잠시 후 다시 시도해주세요.")
            st.stop()

    if not recipes:
        st.warning("추천할 레시피를 찾지 못했습니다. 재료를 더 추가해보세요.")
        st.stop()

    st.session_state["recipes"] = recipes

# 레시피 결과 표시
if "recipes" in st.session_state:
    recipes = st.session_state["recipes"]
    st.subheader(f"추천 레시피 ({len(recipes)}개)")

    for i, recipe in enumerate(recipes):
        diff = recipe.get("difficulty", "보통")
        time_est = recipe.get("time", "?")
        missing = set(recipe.get("missing", []))
        substitutions = recipe.get("substitutions", {})

        with st.expander(
            f"**{recipe['name']}** — {recipe.get('description', '')}",
            expanded=(i == 0),
        ):
            # 난이도 & 시간 뱃지
            st.markdown(f"""
            <div style="display:flex; gap:0.6rem; margin-bottom:1rem; font-family:'Noto Sans KR',sans-serif;">
                <span style="background:#f5f5f5; border-radius:20px; padding:0.3rem 0.8rem; font-size:0.82rem;">
                    난이도: {diff}
                </span>
                <span style="background:#f5f5f5; border-radius:20px; padding:0.3rem 0.8rem; font-size:0.82rem;">
                    ⏱ {time_est}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # 재료 표시 (색상 코딩)
            st.markdown("**재료**")
            ingredient_items = ""
            for ing in recipe.get("ingredients", []):
                if ing in missing and ing in substitutions:
                    ingredient_items += (
                        f'<div style="padding:0.3rem 0; color:#e6a700;">'
                        f'🟡 <s>{ing}</s> → 대체 가능</div>'
                    )
                elif ing in missing:
                    ingredient_items += (
                        f'<div style="padding:0.3rem 0; color:#e53e3e; font-weight:500;">'
                        f'🔴 {ing} (부족)</div>'
                    )
                else:
                    ingredient_items += (
                        f'<div style="padding:0.3rem 0; color:#38a169;">'
                        f'🟢 {ing}</div>'
                    )
            st.markdown(f'<div style="margin-bottom:1rem; font-family:\'Noto Sans KR\',sans-serif;">{ingredient_items}</div>', unsafe_allow_html=True)

            # 대체 재료 안내
            if substitutions:
                st.markdown("**대체 재료**")
                for orig, sub_text in substitutions.items():
                    st.markdown(f"- {sub_text}")

            # 단계별 조리법 (개선된 UI)
            st.markdown("**조리법**")
            instructions = recipe.get("instructions", [])
            total_steps = len(instructions)

            step_key = f"step_{i}"
            if step_key not in st.session_state:
                st.session_state[step_key] = 0

            current_step = st.session_state[step_key]

            if total_steps > 0:
                # 진행도 표시
                progress = (current_step + 1) / total_steps
                st.progress(progress, text=f"단계 {current_step + 1} / {total_steps}")

                # 현재 단계 표시
                st.markdown(f"""
                <div style="background:#f8f9fa; border-radius:12px; padding:1rem; margin:0.5rem 0;
                            font-family:'Noto Sans KR',sans-serif; font-size:1rem; line-height:1.6;">
                    {instructions[current_step]}
                </div>
                """, unsafe_allow_html=True)

                # 이전/다음 버튼
                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                with nav_col1:
                    if st.button("⬅ 이전", key=f"prev_{i}", use_container_width=True,
                                 disabled=(current_step == 0)):
                        st.session_state[step_key] = current_step - 1
                        st.rerun()
                with nav_col2:
                    if st.button("전체 보기", key=f"all_{i}", use_container_width=True):
                        st.session_state[f"show_all_{i}"] = not st.session_state.get(f"show_all_{i}", False)
                        st.rerun()
                with nav_col3:
                    if st.button("다음 ➡", key=f"next_{i}", use_container_width=True,
                                 disabled=(current_step >= total_steps - 1)):
                        st.session_state[step_key] = current_step + 1
                        st.rerun()

                # 전체 보기 모드
                if st.session_state.get(f"show_all_{i}", False):
                    for step in instructions:
                        st.markdown(f"- {step}")

            st.markdown("---")

            # 액션 버튼: 저장 + 장보기 추가
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                if st.button("💾 레시피 저장", key=f"save_{i}", use_container_width=True):
                    save_recipe(recipe)
                    st.success(f"'{recipe['name']}' 저장 완료!")
            with act_col2:
                missing_list = [m for m in missing if m not in substitutions]
                if missing_list:
                    if st.button(f"🛒 부족재료 장보기 추가 ({len(missing_list)}개)", key=f"shop_{i}",
                                 use_container_width=True):
                        add_missing_to_shopping(missing_list)
                        st.success(f"{len(missing_list)}개 재료가 장보기 목록에 추가되었습니다!")
                else:
                    st.caption("모든 재료를 보유하고 있습니다!")
