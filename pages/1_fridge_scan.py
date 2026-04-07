import os

import streamlit as st
from db.database import init_db
from db.repository import upsert_ingredients
from services.vision import analyze_multiple_images

init_db()

st.header("냉장고 스캔")
st.markdown("냉장고 사진을 업로드하면 재료를 자동으로 인식합니다.")

# API 키 확인
if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_api_key_here":
    st.warning("`.env` 파일에 `ANTHROPIC_API_KEY`를 설정해주세요.")
    st.stop()

# 이미지 업로드
uploaded_files = st.file_uploader(
    "냉장고 사진 업로드 (여러 장 가능)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    # 미리보기
    cols = st.columns(min(len(uploaded_files), 3))
    for i, f in enumerate(uploaded_files):
        with cols[i % 3]:
            st.image(f, caption=f.name, use_container_width=True)

    # 스캔 버튼
    if st.button("재료 스캔 시작", type="primary", use_container_width=True):
        images = []
        for f in uploaded_files:
            content_type = f.type or "image/jpeg"
            images.append((f.getvalue(), content_type))

        with st.spinner("AI가 재료를 분석하고 있습니다..."):
            try:
                detected = analyze_multiple_images(images)
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
                st.stop()

        if not detected:
            st.warning("감지된 재료가 없습니다. 다른 사진을 시도해보세요.")
            st.stop()

        # 세션에 저장하여 체크리스트 표시
        st.session_state["detected_ingredients"] = detected

# 감지 결과 체크리스트
if "detected_ingredients" in st.session_state:
    detected = st.session_state["detected_ingredients"]
    st.subheader(f"감지된 재료 ({len(detected)}개)")
    st.markdown("저장하지 않을 재료는 체크를 해제하세요.")

    selected = []
    for i, item in enumerate(detected):
        checked = st.checkbox(
            f"{item['name']} ({item.get('category', '기타')})",
            value=True,
            key=f"check_{i}",
        )
        if checked:
            selected.append(item)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("선택한 재료 저장", type="primary", use_container_width=True):
            if selected:
                upsert_ingredients(selected, source="scan")
                st.success(f"{len(selected)}개 재료가 저장되었습니다!")
                del st.session_state["detected_ingredients"]
                st.rerun()
            else:
                st.warning("저장할 재료를 선택해주세요.")
    with col2:
        if st.button("결과 초기화", use_container_width=True):
            del st.session_state["detected_ingredients"]
            st.rerun()
