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

cards = [
    ("📷", "fridge_scan", "fridge_scan_desc", "#fff5f5"),
    ("🥬", "ingredients", "ingredients_desc", "#f0f7ff"),
    ("🍽️", "recipes", "recipes_desc", "#f0fff4"),
    ("📚", "saved_recipes", "saved_recipes_desc", "#fff8f0"),
    ("🛒", "shopping", "shopping_desc", "#f5f0ff"),
    ("👤", "profile", "profile_desc", "#f0f0f0"),
]

cards_html = ""
for icon, title_key, desc_key, bg in cards:
    cards_html += (
        f'<div style="flex:1 1 calc(33% - 0.7rem); min-width:140px; background:{bg};'
        f' border-radius:16px; padding:1rem 1.2rem; box-sizing:border-box;">'
        f'<div style="font-size:1.3rem; margin-bottom:0.2rem;">{icon}</div>'
        f'<div style="font-weight:600; font-size:0.9rem; margin-bottom:0.2rem;">{t(title_key)}</div>'
        f'<div style="font-size:0.78rem; color:#555;">{t(desc_key)}</div>'
        f'</div>'
    )

st.markdown(
    f'<div style="display:flex; flex-wrap:wrap; gap:0.6rem; margin:1rem 0; font-family:\'Noto Sans KR\',sans-serif;">'
    f'{cards_html}</div>',
    unsafe_allow_html=True,
)

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
