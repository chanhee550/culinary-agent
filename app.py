import streamlit as st
from dotenv import load_dotenv
from db.database import init_db
from db.repository import get_all_ingredients, get_expiring_ingredients, get_shopping_list, get_profile
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
