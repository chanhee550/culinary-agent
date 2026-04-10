import streamlit as st
from db.database import init_db
from db.repository import get_profile, update_profile
from styles import apply_global_styles

init_db()
apply_global_styles()

st.header("👤 프로필 설정")
st.caption("설정한 정보가 AI 레시피 추천에 반영됩니다.")

profile = get_profile()

SKILL_LEVELS = ["초보", "중급", "고급"]
SKILL_DESCRIPTIONS = {
    "초보": "요리를 처음 배우는 단계. 간단한 레시피 위주로 추천합니다.",
    "중급": "기본 기술을 보유. 다양한 요리에 도전할 수 있습니다.",
    "고급": "다양한 기술 활용 가능. 복잡한 레시피도 추천합니다.",
}

CUISINE_OPTIONS = ["한식", "양식", "중식", "일식", "이탈리안", "멕시칸", "퓨전", "비건", "저염식"]
TASTE_OPTIONS = ["매운맛", "단맛", "짠맛", "신맛", "감칠맛", "담백한맛"]
ALLERGY_OPTIONS = ["우유", "계란", "견과류", "갑각류", "조개류", "생선", "콩", "밀", "참깨", "복숭아"]

# --- 숙련도 설정 ---
st.subheader("요리 숙련도")

current_skill_idx = SKILL_LEVELS.index(profile.skill_level) if profile.skill_level in SKILL_LEVELS else 0
skill_level = st.radio(
    "숙련도를 선택하세요",
    SKILL_LEVELS,
    index=current_skill_idx,
    horizontal=True,
    label_visibility="collapsed",
)
st.caption(SKILL_DESCRIPTIONS[skill_level])

# --- 요리 종류 선호도 ---
st.subheader("선호 요리 종류")
st.caption("좋아하는 요리 종류를 모두 선택하세요. AI가 해당 종류를 우선 추천합니다.")

current_cuisines = [c.strip() for c in profile.cuisine_preference.split(",") if c.strip()]
selected_cuisines = []
cols = st.columns(3)
for i, cuisine in enumerate(CUISINE_OPTIONS):
    with cols[i % 3]:
        if st.checkbox(cuisine, value=(cuisine in current_cuisines), key=f"cuisine_{i}"):
            selected_cuisines.append(cuisine)

# --- 맛 선호도 ---
st.subheader("맛 선호도")
st.caption("좋아하는 맛을 선택하세요.")

current_tastes = [t.strip() for t in profile.taste_preference.split(",") if t.strip()]
selected_tastes = []
cols = st.columns(3)
for i, taste in enumerate(TASTE_OPTIONS):
    with cols[i % 3]:
        if st.checkbox(taste, value=(taste in current_tastes), key=f"taste_{i}"):
            selected_tastes.append(taste)

# --- 알레르기 정보 ---
st.subheader("알레르기 정보")
st.caption("알레르기 유발 재료를 선택하면, 해당 재료가 포함된 레시피를 자동으로 제외합니다.")

current_allergies = [a.strip() for a in profile.allergies.split(",") if a.strip()]
selected_allergies = []
cols = st.columns(3)
for i, allergy in enumerate(ALLERGY_OPTIONS):
    with cols[i % 3]:
        if st.checkbox(allergy, value=(allergy in current_allergies), key=f"allergy_{i}"):
            selected_allergies.append(allergy)

# 커스텀 알레르기 추가
custom_allergy = st.text_input("기타 알레르기 재료 (쉼표로 구분)", placeholder="예: 키위, 망고")
if custom_allergy.strip():
    for item in custom_allergy.split(","):
        item = item.strip()
        if item and item not in selected_allergies:
            selected_allergies.append(item)

# --- 저장 버튼 ---
st.markdown("---")
if st.button("프로필 저장", type="primary", use_container_width=True):
    update_profile(
        skill_level=skill_level,
        cuisine_preference=",".join(selected_cuisines),
        taste_preference=",".join(selected_tastes),
        allergies=",".join(selected_allergies),
    )
    st.success("프로필이 저장되었습니다!")

# --- 현재 설정 요약 ---
st.markdown("---")
st.subheader("현재 설정 요약")

summary_items = [
    ("숙련도", profile.skill_level),
    ("선호 요리", profile.cuisine_preference or "미설정"),
    ("맛 선호", profile.taste_preference or "미설정"),
    ("알레르기", profile.allergies or "없음"),
]

for label, value in summary_items:
    st.markdown(f"**{label}:** {value}")
