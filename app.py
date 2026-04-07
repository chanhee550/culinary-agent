import streamlit as st
from dotenv import load_dotenv
from db.database import init_db

load_dotenv()
init_db()

st.set_page_config(
    page_title="Culinary Agent",
    page_icon="🍳",
    layout="wide",
)

st.title("Culinary Agent")
st.markdown("냉장고 속 재료를 관리하고, 맞춤 레시피를 추천받으세요.")

st.markdown("""
### 사용 방법
1. **냉장고 스캔** - 냉장고 사진을 업로드하면 재료를 자동으로 인식합니다
2. **재료 관리** - 재료를 직접 추가/수정/삭제할 수 있습니다
3. **레시피 추천** - 보유 재료 기반으로 레시피를 추천받습니다
""")

# 사이드바에 현재 재료 수 표시
from db.repository import get_all_ingredients

ingredients = get_all_ingredients()
st.sidebar.metric("보유 재료", f"{len(ingredients)}개")

if ingredients:
    categories = {}
    for ing in ingredients:
        categories.setdefault(ing.category, []).append(ing.name)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**카테고리별 재료**")
    for cat, names in sorted(categories.items()):
        st.sidebar.markdown(f"- **{cat}**: {', '.join(names)}")
