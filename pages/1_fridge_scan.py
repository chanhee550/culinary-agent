import os

import streamlit as st
from db.storage import upsert_ingredients, init_db
from services.vision import analyze_multiple_images

init_db()

CATEGORIES = ["채소", "과일", "육류", "해산물", "유제품", "양념/소스",
              "곡류/면", "음료", "냉동식품", "기타"]

st.header("냉장고 스캔")
st.markdown("냉장고 사진을 업로드하면 AI가 재료를 자동으로 인식합니다. "
            "통/병에 담긴 음식은 직접 알려주세요.")

if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_api_key_here":
    st.warning("`.env` 파일에 `ANTHROPIC_API_KEY`를 설정해주세요.")
    st.stop()

uploaded_files = st.file_uploader(
    "냉장고 사진 업로드 (여러 장 가능)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 3))
    for i, f in enumerate(uploaded_files):
        with cols[i % 3]:
            st.image(f, caption=f"#{i+1} {f.name}", use_container_width=True)

    if st.button("재료 스캔 시작", type="primary", use_container_width=True):
        images = [(f.getvalue(), f.type or "image/jpeg") for f in uploaded_files]

        with st.spinner("AI가 재료를 분석하고 있습니다..."):
            try:
                result = analyze_multiple_images(images)
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
                st.stop()

        if not result["confirmed"] and not result["unknowns"]:
            st.warning("감지된 재료가 없습니다. 다른 사진을 시도해보세요.")
            st.stop()

        st.session_state["scan_result"] = result


if "scan_result" in st.session_state:
    result = st.session_state["scan_result"]
    confirmed = result["confirmed"]
    unknowns = result["unknowns"]

    # --- 1) 확정 재료 ---
    confirmed_selected: list[dict] = []
    if confirmed:
        st.subheader(f"✅ 인식된 재료 ({len(confirmed)}개)")
        st.caption("저장하지 않을 재료는 체크 해제하세요.")

        for i, item in enumerate(confirmed):
            label = f"{item['name']} ({item.get('category', '기타')})"
            if item.get("quantity"):
                label += f" · {item['quantity']}"
            if st.checkbox(label, value=True, key=f"conf_{i}"):
                confirmed_selected.append({
                    "name": item["name"],
                    "category": item.get("category", "기타"),
                    "quantity": item.get("quantity"),
                })

    # --- 2) 불확실 항목 — 사용자 입력 ---
    unknown_filled: list[dict] = []
    if unknowns:
        st.subheader(f"❓ 직접 알려주세요 ({len(unknowns)}개)")
        st.caption("AI가 통·병에 담긴 음식은 정확히 알 수 없어요. "
                   "비워두면 저장되지 않습니다.")

        for unk in unknowns:
            uid = unk["id"]
            with st.container(border=True):
                st.markdown(f"**📦 {unk.get('description', '알 수 없는 항목')}**")

                meta_parts = []
                if unk.get("location"):
                    meta_parts.append(f"📍 {unk['location']}")
                if unk.get("image_index") is not None:
                    meta_parts.append(f"🖼️ 사진 #{unk['image_index'] + 1}")
                if meta_parts:
                    st.caption(" · ".join(meta_parts))

                guess = unk.get("guess", "") or ""
                default_name = guess.split(" 또는 ")[0].strip() if guess else ""

                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    name = st.text_input(
                        "재료명",
                        value=default_name,
                        key=f"unk_name_{uid}",
                        placeholder="예: 김치, 토마토소스",
                    )
                with col2:
                    category = st.selectbox(
                        "카테고리",
                        CATEGORIES,
                        index=CATEGORIES.index("양념/소스"),
                        key=f"unk_cat_{uid}",
                    )
                with col3:
                    quantity = st.text_input(
                        "수량 (선택)",
                        key=f"unk_qty_{uid}",
                        placeholder="예: 1통",
                    )

                if guess:
                    st.caption(f"💡 AI 추측: {guess}")

                if name.strip():
                    unknown_filled.append({
                        "name": name.strip(),
                        "category": category,
                        "quantity": quantity.strip() or None,
                    })

    # --- 3) 통합 저장 ---
    st.markdown("---")
    total = len(confirmed_selected) + len(unknown_filled)
    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button(
            f"선택한 재료 모두 저장 ({total}개)",
            type="primary",
            use_container_width=True,
            disabled=(total == 0),
        ):
            upsert_ingredients(confirmed_selected + unknown_filled, source="scan")
            st.success(f"{total}개 재료가 저장되었습니다!")
            del st.session_state["scan_result"]
            st.rerun()
    with col_reset:
        if st.button("결과 초기화", use_container_width=True):
            del st.session_state["scan_result"]
            st.rerun()
