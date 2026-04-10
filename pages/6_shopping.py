import streamlit as st
from db.database import init_db
from db.repository import (
    get_shopping_list, add_shopping_item,
    toggle_shopping_item, delete_shopping_item,
    clear_checked_shopping,
)
from styles import apply_global_styles

init_db()
apply_global_styles()

st.header("🛒 장보기 목록")
st.caption("부족한 재료를 관리하고, 마트 방문 시 참고하세요.")

CATEGORIES = ["채소", "과일", "육류", "해산물", "유제품", "양념/소스", "곡류/면", "음료", "냉동식품", "기타"]

# --- 수동 추가 ---
with st.form("add_shopping", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        name = st.text_input("재료명", placeholder="예: 두부", label_visibility="collapsed")
    with col2:
        quantity = st.text_input("수량", placeholder="수량", label_visibility="collapsed")
    with col3:
        if st.form_submit_button("추가", use_container_width=True):
            if name.strip():
                add_shopping_item(name.strip(), quantity.strip() or None)
                st.rerun()

# --- 목록 표시 ---
items = get_shopping_list()

if not items:
    st.info("장보기 목록이 비어있습니다. 레시피 추천에서 부족 재료를 추가하거나 위에서 직접 추가하세요.")
    st.stop()

unchecked = [it for it in items if not it.checked]
checked = [it for it in items if it.checked]

# 미체크 항목
if unchecked:
    st.subheader(f"구매 필요 ({len(unchecked)}개)")
    for item in unchecked:
        col_check, col_name, col_qty, col_del = st.columns([0.5, 3, 1.5, 0.8])
        with col_check:
            if st.checkbox("", key=f"check_{item.id}", value=False):
                toggle_shopping_item(item.id)
                st.rerun()
        with col_name:
            st.markdown(f"**{item.name}**")
        with col_qty:
            st.caption(item.quantity or "-")
        with col_del:
            if st.button("✕", key=f"del_shop_{item.id}", use_container_width=True):
                delete_shopping_item(item.id)
                st.rerun()

# 체크된 항목
if checked:
    st.markdown("---")
    st.subheader(f"구매 완료 ({len(checked)}개)")
    for item in checked:
        col_check, col_name, col_qty, col_del = st.columns([0.5, 3, 1.5, 0.8])
        with col_check:
            if st.checkbox("", key=f"check_{item.id}", value=True):
                toggle_shopping_item(item.id)
                st.rerun()
        with col_name:
            st.markdown(f"~~{item.name}~~")
        with col_qty:
            st.caption(item.quantity or "-")
        with col_del:
            if st.button("✕", key=f"del_shop_{item.id}", use_container_width=True):
                delete_shopping_item(item.id)
                st.rerun()

    if st.button("완료 항목 모두 삭제", use_container_width=True):
        clear_checked_shopping()
        st.rerun()

# 하단 요약
st.markdown("---")
st.caption(f"총 {len(items)}개 항목 (구매 필요: {len(unchecked)} / 완료: {len(checked)})")
