import streamlit as st
from dotenv import load_dotenv
from db.database import init_db
from db.repository import (
    get_all_ingredients, get_expiring_ingredients, get_shopping_list, get_profile,
    get_ingredient_names, get_today_recipes, save_today_recipes, clear_today_recipes,
    prune_old_daily_recipes,
)
from services.recipe import recommend_recipes
from styles import apply_global_styles
from i18n import t, language_selector

load_dotenv()
init_db()

st.set_page_config(
    page_title="Culinary Agent",
    page_icon="🍳",
    layout="wide",
)

apply_global_styles()

# 언어 선택기 (사이드바 상단)
language_selector()

# 다크/라이트 모드 전환
st.sidebar.markdown("---")
theme_label = "🌙 Dark" if not st.session_state.get("dark_mode", False) else "☀️ Light"
if st.sidebar.button(theme_label, use_container_width=True, key="theme_toggle"):
    st.session_state["dark_mode"] = not st.session_state.get("dark_mode", False)
    st.rerun()

if st.session_state.get("dark_mode", False):
    st.markdown("""
    <style>
    .stApp, .main, [data-testid="stAppViewContainer"] {
        background-color: #0e1117 !important;
        color: #e0e0e0 !important;
    }
    .stApp p, .stApp span, .stApp div, .stApp li, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #e0e0e0 !important;
    }
    section[data-testid="stSidebar"] {
        background: #161616 !important;
    }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] div {
        color: #ccc !important;
    }
    div[data-testid="stMetric"] {
        background: #1e1e1e !important;
    }
    div[data-testid="stMetric"] label { color: #aaa !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #f0f0f0 !important; }
    div[data-testid="stExpander"] { background: #1e1e1e !important; }
    div[data-testid="stForm"] { background: #1a1a1a !important; }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-bottom-color: #444 !important;
        color: #e0e0e0 !important;
        background: transparent !important;
    }
    .stButton > button:not([kind="primary"]) {
        background: #2a2a2a !important;
        color: #e0e0e0 !important;
    }
    div[data-testid="stFileUploader"] > div {
        border-color: #444 !important;
        background: #1a1a1a !important;
    }
    hr { border-top-color: #333 !important; }
    /* Inline HTML backgrounds */
    .stMarkdown div[style*="background:#f"], .stMarkdown span[style*="background:#f"] {
        background: #2a2a2a !important;
        color: #e0e0e0 !important;
    }
    .stMarkdown div[style*="color:#555"], .stMarkdown div[style*="color:#333"],
    .stMarkdown span[style*="color:#555"], .stMarkdown span[style*="color:#333"] {
        color: #ccc !important;
    }
    </style>
    """, unsafe_allow_html=True)
st.sidebar.markdown("---")

st.title(t("app_title"))
st.markdown(t("app_subtitle"))

# --- 오늘의 레시피 ---
prune_old_daily_recipes(keep_days=7)

st.markdown(f"""
<div style="background:linear-gradient(135deg,#fff8e1 0%,#ffe9c2 100%); border-radius:16px; padding:1rem 1.2rem; margin:1.2rem 0 0.8rem; font-family:'Noto Sans KR',sans-serif;">
    <div style="font-weight:700; font-size:1.1rem; color:#5d4037;">{t("today_recipes_title")}</div>
    <div style="font-size:0.85rem; color:#7b6a5d; margin-top:2px;">{t("today_recipes_subtitle")}</div>
</div>
""", unsafe_allow_html=True)

_today_recipes = get_today_recipes()
_ing_names = get_ingredient_names()

if _today_recipes is None and not _ing_names:
    st.info(t("today_recipes_empty"))
elif _today_recipes is None:
    # 첫 방문 (오늘 캐시 없음) → 사용자가 직접 트리거
    if st.button(t("today_recipes_get"), type="primary", use_container_width=True, key="today_get"):
        with st.spinner(t("today_recipes_loading")):
            try:
                generated = recommend_recipes(_ing_names, max_missing=2)[:3]
            except Exception as e:
                st.error(f"{t('today_recipes_failed')}: {e}")
                generated = []
        if generated:
            save_today_recipes(generated)
            st.rerun()
else:
    # 캐시된 오늘의 레시피 표시
    cols = st.columns(min(len(_today_recipes), 3))
    for idx, recipe in enumerate(_today_recipes[:3]):
        with cols[idx]:
            with st.container(border=True):
                st.markdown(f"**{recipe.get('name', '')}**")
                if recipe.get("description"):
                    st.caption(recipe["description"])
                meta = []
                if recipe.get("difficulty"):
                    meta.append(recipe["difficulty"])
                if recipe.get("time"):
                    meta.append(f"🕐 {recipe['time']}")
                if meta:
                    st.caption(" · ".join(meta))

                with st.expander(t("today_recipes_view")):
                    if recipe.get("ingredients"):
                        st.markdown(
                            f"**{t('today_recipes_ingredients_label')}**: "
                            + ", ".join(recipe["ingredients"])
                        )
                    if recipe.get("missing"):
                        st.markdown(
                            f"**{t('today_recipes_missing_label')}**: "
                            + ", ".join(recipe["missing"])
                        )
                    if recipe.get("instructions"):
                        st.markdown(f"**{t('today_recipes_steps_label')}**")
                        for step in recipe["instructions"]:
                            st.markdown(step)

    refresh_col1, _refresh_col2 = st.columns([1, 4])
    with refresh_col1:
        if st.button(
            t("today_recipes_refresh"),
            help=t("today_recipes_refresh_help"),
            key="today_refresh",
        ):
            clear_today_recipes()
            st.rerun()

st.markdown("---")

# 카드 버튼 스타일
st.markdown("""
<style>
div.stButton > button {
    min-height: 80px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    white-space: pre-line !important;
    text-align: left !important;
    padding: 1rem !important;
    border-radius: 16px !important;
}
</style>
""", unsafe_allow_html=True)

cards = [
    ("📷", "fridge_scan", "fridge_scan_desc", "1_📷_냉장고 스캔"),
    ("🥬", "ingredients", "ingredients_desc", "2_🥬_재료 관리"),
    ("🍽️", "recipes", "recipes_desc", "3_🍽️_레시피 추천"),
    ("📚", "saved_recipes", "saved_recipes_desc", "5_📚_저장 레시피"),
    ("🛒", "shopping", "shopping_desc", "6_🛒_장보기 목록"),
    ("👤", "profile", "profile_desc", "4_👤_프로필 설정"),
]

col1, col2 = st.columns(2)
for i, (icon, title_key, desc_key, page_name) in enumerate(cards):
    with (col1 if i % 2 == 0 else col2):
        if st.button(
            f"{icon} {t(title_key)}\n{t(desc_key)}",
            key=f"card_{i}",
            use_container_width=True,
        ):
            st.switch_page(f"pages/{page_name}.py")

# --- 사이드바 대시보드 ---
ingredients = get_all_ingredients()
expiring = get_expiring_ingredients(days=3)
shopping = get_shopping_list()
profile = get_profile()

st.sidebar.metric(t("owned_ingredients"), f"{len(ingredients)}")

if expiring:
    st.sidebar.markdown(f"⚠️ **{t('expiry_warning')}: {len(expiring)}**")
    for ing in expiring:
        st.sidebar.caption(f"- {ing.name} ({ing.expiry_date})")

unchecked_shopping = [s for s in shopping if not s.checked]
if unchecked_shopping:
    st.sidebar.markdown(f"🛒 **{t('shopping_label')}: {len(unchecked_shopping)}**")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{t('skill_level')}:** {profile.skill_level}")
if profile.allergies:
    st.sidebar.caption(f"{t('allergy')}: {profile.allergies}")

if ingredients:
    categories = {}
    for ing in ingredients:
        categories.setdefault(ing.category, []).append(ing.name)
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**{t('category_ingredients')}**")
    for cat, names in sorted(categories.items()):
        st.sidebar.markdown(f"- **{cat}**: {', '.join(names)}")
