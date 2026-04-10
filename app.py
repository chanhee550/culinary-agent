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
