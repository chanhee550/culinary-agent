import streamlit as st
from dotenv import load_dotenv
from db.database import init_db
from db.repository import get_all_ingredients, get_expiring_ingredients, get_shopping_list, get_profile
from styles import apply_global_styles

load_dotenv()
init_db()

st.set_page_config(
    page_title="Culinary Agent",
    page_icon="🍳",
    layout="wide",
)

apply_global_styles()

st.title("Culinary Agent")
st.markdown("냉장고 속 재료를 관리하고, 맞춤 레시피를 추천받으세요.")

st.markdown("""
<div style="display:flex; flex-wrap:wrap; gap:1rem; margin:1.5rem 0; font-family:'Noto Sans KR',sans-serif;">
    <div style="flex:1; min-width:160px; background:#fff5f5; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">📷</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">냉장고 스캔</div>
        <div style="font-size:0.85rem; color:#555;">사진으로 재료 자동 인식</div>
    </div>
    <div style="flex:1; min-width:160px; background:#f0f7ff; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">🥬</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">재료 관리</div>
        <div style="font-size:0.85rem; color:#555;">유통기한까지 관리</div>
    </div>
    <div style="flex:1; min-width:160px; background:#f0fff4; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">🍽️</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">레시피 추천</div>
        <div style="font-size:0.85rem; color:#555;">AI 맞춤 추천 + 단계별 가이드</div>
    </div>
    <div style="flex:1; min-width:160px; background:#fff8f0; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">📚</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">저장 레시피</div>
        <div style="font-size:0.85rem; color:#555;">마음에 드는 레시피 보관</div>
    </div>
    <div style="flex:1; min-width:160px; background:#f5f0ff; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">🛒</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">장보기 목록</div>
        <div style="font-size:0.85rem; color:#555;">부족 재료 자동 추가</div>
    </div>
    <div style="flex:1; min-width:160px; background:#f0f0f0; border-radius:16px; padding:1.2rem 1.4rem;">
        <div style="font-size:1.5rem; margin-bottom:0.3rem;">👤</div>
        <div style="font-weight:600; margin-bottom:0.3rem;">프로필 설정</div>
        <div style="font-size:0.85rem; color:#555;">선호도 · 알레르기 관리</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 사이드바 대시보드 ---
ingredients = get_all_ingredients()
expiring = get_expiring_ingredients(days=3)
shopping = get_shopping_list()
profile = get_profile()

st.sidebar.metric("보유 재료", f"{len(ingredients)}개")

# 유통기한 임박 경고
if expiring:
    st.sidebar.markdown(f"⚠️ **유통기한 임박: {len(expiring)}개**")
    for ing in expiring:
        st.sidebar.caption(f"- {ing.name} ({ing.expiry_date})")

# 장보기 목록 요약
unchecked_shopping = [s for s in shopping if not s.checked]
if unchecked_shopping:
    st.sidebar.markdown(f"🛒 **장보기: {len(unchecked_shopping)}개**")

# 프로필 요약
st.sidebar.markdown("---")
st.sidebar.markdown(f"**숙련도:** {profile.skill_level}")
if profile.allergies:
    st.sidebar.caption(f"알레르기: {profile.allergies}")

# 카테고리별 재료
if ingredients:
    categories = {}
    for ing in ingredients:
        categories.setdefault(ing.category, []).append(ing.name)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**카테고리별 재료**")
    for cat, names in sorted(categories.items()):
        st.sidebar.markdown(f"- **{cat}**: {', '.join(names)}")
