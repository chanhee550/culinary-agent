import os

import streamlit as st
from db.database import init_db
from db.repository import upsert_ingredients
from services.vision import analyze_multiple_images
from styles import apply_global_styles

init_db()
apply_global_styles()

CATEGORIES = ["채소", "과일", "육류", "해산물", "유제품", "계란",
              "양념/소스", "곡류/면", "음료", "냉동식품", "가공식품", "기타"]

SCAN_SHOTS = [
    ("전체", "냉장고 문을 열고 전체가 보이게 1장"),
    ("선반", "각 선반을 가까이서 1장씩"),
    ("도어", "문쪽 포켓의 병·소스 라벨이 보이게 1장"),
    ("서랍", "야채칸/냉동칸을 열고 1장"),
    ("라벨", "이름이 작은 통·병은 라벨 근접 사진 추가"),
]

st.header("📷 냉장고 스캔")
st.caption("냉장고 사진을 업로드하면 AI가 재료를 자동으로 인식합니다. "
           "통/병에 담긴 음식은 직접 알려주세요.")

# API 키 확인
if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_api_key_here":
    st.warning("`.env` 파일에 `ANTHROPIC_API_KEY`를 설정해주세요.")
    st.stop()

# --- 촬영 가이드 ---
with st.container(border=True):
    st.markdown("**정확도를 높이는 촬영 순서**")
    guide_cols = st.columns(len(SCAN_SHOTS))
    for idx, (title, desc) in enumerate(SCAN_SHOTS):
        with guide_cols[idx]:
            st.markdown(f"**{idx + 1}. {title}**")
            st.caption(desc)

st.info("권장: 최소 4장 이상. 전체 사진만으로는 작은 재료와 라벨이 누락될 수 있어요.")

# --- 이미지 업로드 ---
uploaded_files = st.file_uploader(
    "냉장고 사진 업로드 (가이드 순서대로 여러 장 권장)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    if len(uploaded_files) < 4:
        st.warning(
            f"현재 {len(uploaded_files)}장입니다. 선반/도어/서랍 근접 사진을 추가하면 인식 정확도가 올라갑니다."
        )
    else:
        st.success(f"{len(uploaded_files)}장이 준비됐습니다. 전체와 근접 사진이 함께 있으면 가장 안정적이에요.")

    # 미리보기
    cols = st.columns(min(len(uploaded_files), 3))
    for i, f in enumerate(uploaded_files):
        with cols[i % 3]:
            st.image(f, caption=f"#{i+1} {f.name}", use_container_width=True)

    st.markdown("")
    if st.button("재료 스캔 시작", type="primary", use_container_width=True):
        images = [(f.getvalue(), f.type or "image/jpeg") for f in uploaded_files]

        with st.spinner("AI가 재료를 분석하고 있습니다..."):
            try:
                result = analyze_multiple_images(images)
            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {e}")
                st.stop()

        for err in result.get("errors", []):
            st.warning(err)
        for warning in result.get("quality_warnings", []):
            st.info(warning)

        if not result["confirmed"] and not result["unknowns"]:
            st.error("감지된 재료가 없습니다. 다른 사진을 시도해보세요.")
            st.stop()

        st.session_state["scan_result"] = result


# --- 결과 처리 ---
if "scan_result" in st.session_state:
    result = st.session_state["scan_result"]
    confirmed = result.get("confirmed", [])
    unknowns = result.get("unknowns", [])

    # 1) 확정 재료 — 체크박스
    confirmed_selected: list[dict] = []
    if confirmed:
        st.markdown(f"""
        <div style="background:#f0fff4; border-radius:12px; padding:0.8rem 1rem; margin:1rem 0; font-family:'Noto Sans KR',sans-serif;">
            <span style="font-weight:600;">✅ 인식된 재료 {len(confirmed)}개</span>
            <span style="font-size:0.85rem; color:#555;"> — 저장하지 않을 재료는 체크를 해제하세요</span>
        </div>
        """, unsafe_allow_html=True)

        for i, item in enumerate(confirmed):
            label = f"{item['name']}  `{item.get('category', '기타')}`"
            if item.get("quantity"):
                label += f" · {item['quantity']}"
            checked = st.checkbox(label, value=True, key=f"conf_{i}")
            if checked:
                confirmed_selected.append({
                    "name": item["name"],
                    "category": item.get("category", "기타"),
                    "quantity": item.get("quantity"),
                })

    # 2) 불확실 항목 — 사용자 직접 입력
    unknown_filled: list[dict] = []
    if unknowns:
        st.markdown(f"""
        <div style="background:#fff7e6; border-radius:12px; padding:0.8rem 1rem; margin:1rem 0; font-family:'Noto Sans KR',sans-serif;">
            <span style="font-weight:600;">❓ 직접 알려주세요 {len(unknowns)}개</span>
            <span style="font-size:0.85rem; color:#555;"> — AI가 통/병에 담긴 음식은 정확히 알 수 없어요. 비워두면 저장되지 않습니다.</span>
        </div>
        """, unsafe_allow_html=True)

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
                        label_visibility="collapsed",
                    )
                with col2:
                    cat_default = "양념/소스" if "양념/소스" in CATEGORIES else "기타"
                    category = st.selectbox(
                        "카테고리",
                        CATEGORIES,
                        index=CATEGORIES.index(cat_default),
                        key=f"unk_cat_{uid}",
                        label_visibility="collapsed",
                    )
                with col3:
                    quantity = st.text_input(
                        "수량",
                        key=f"unk_qty_{uid}",
                        placeholder="수량 (선택)",
                        label_visibility="collapsed",
                    )

                if guess:
                    st.caption(f"💡 AI 추측: {guess}")

                if name.strip():
                    unknown_filled.append({
                        "name": name.strip(),
                        "category": category,
                        "quantity": quantity.strip() or None,
                    })

    # 3) 통합 저장
    st.markdown("---")
    total_to_save = len(confirmed_selected) + len(unknown_filled)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            f"선택한 재료 저장 ({total_to_save}개)",
            type="primary",
            use_container_width=True,
            disabled=(total_to_save == 0),
        ):
            upsert_ingredients(confirmed_selected + unknown_filled, source="scan")
            st.success(f"{total_to_save}개 재료가 저장되었습니다!")
            del st.session_state["scan_result"]
            st.rerun()
    with col2:
        if st.button("결과 초기화", use_container_width=True):
            del st.session_state["scan_result"]
            st.rerun()
