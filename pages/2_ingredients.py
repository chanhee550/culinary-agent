import streamlit as st
from db.database import init_db
from db.repository import (
    get_all_ingredients,
    add_ingredient,
    update_ingredient,
    delete_ingredient,
    clear_all,
)

init_db()

st.header("재료 관리")

CATEGORIES = ["채소", "과일", "육류", "해산물", "유제품", "양념/소스", "곡류/면", "음료", "냉동식품", "기타"]

# --- 재료 추가 폼 ---
st.subheader("재료 추가")
with st.form("add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        name = st.text_input("재료명", placeholder="예: 당근")
    with col2:
        category = st.selectbox("카테고리", CATEGORIES)
    with col3:
        quantity = st.text_input("수량", placeholder="예: 3개")
    submitted = st.form_submit_button("추가", use_container_width=True)
    if submitted and name.strip():
        add_ingredient(name.strip(), category, quantity.strip() or None)
        st.success(f"'{name.strip()}' 추가 완료!")
        st.rerun()

# --- 재료 목록 ---
st.subheader("보유 재료 목록")

ingredients = get_all_ingredients()

if not ingredients:
    st.info("등록된 재료가 없습니다. 위에서 재료를 추가하거나 '냉장고 스캔' 페이지를 이용해보세요.")
else:
    # 카테고리 필터
    all_cats = sorted(set(ing.category for ing in ingredients))
    selected_cat = st.selectbox("카테고리 필터", ["전체"] + all_cats)

    filtered = ingredients if selected_cat == "전체" else [i for i in ingredients if i.category == selected_cat]

    for ing in filtered:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
        with col1:
            st.text(ing.name)
        with col2:
            st.text(ing.category)
        with col3:
            st.text(ing.quantity or "-")
        with col4:
            if st.button("수정", key=f"edit_{ing.id}"):
                st.session_state[f"editing_{ing.id}"] = True
        with col5:
            if st.button("삭제", key=f"del_{ing.id}"):
                delete_ingredient(ing.id)
                st.rerun()

        # 수정 모드
        if st.session_state.get(f"editing_{ing.id}", False):
            with st.form(f"edit_form_{ing.id}"):
                ec1, ec2, ec3 = st.columns([2, 1, 1])
                with ec1:
                    new_name = st.text_input("재료명", value=ing.name, key=f"ename_{ing.id}")
                with ec2:
                    new_cat = st.selectbox(
                        "카테고리",
                        CATEGORIES,
                        index=CATEGORIES.index(ing.category) if ing.category in CATEGORIES else len(CATEGORIES) - 1,
                        key=f"ecat_{ing.id}",
                    )
                with ec3:
                    new_qty = st.text_input("수량", value=ing.quantity or "", key=f"eqty_{ing.id}")
                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if st.form_submit_button("저장"):
                        update_ingredient(ing.id, name=new_name.strip(), category=new_cat, quantity=new_qty.strip() or None)
                        st.session_state[f"editing_{ing.id}"] = False
                        st.rerun()
                with ecol2:
                    if st.form_submit_button("취소"):
                        st.session_state[f"editing_{ing.id}"] = False
                        st.rerun()

    st.markdown("---")
    st.markdown(f"**총 {len(filtered)}개 재료** (전체 {len(ingredients)}개)")

    # 전체 삭제
    with st.expander("위험 구역"):
        if st.button("모든 재료 삭제", type="primary"):
            clear_all()
            st.rerun()
