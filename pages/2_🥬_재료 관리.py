from datetime import date, datetime

import streamlit as st
from db.database import init_db
from db.repository import (
    get_all_ingredients,
    add_ingredient,
    update_ingredient,
    delete_ingredient,
    get_expiring_ingredients,
    clear_all,
)
from styles import apply_global_styles

init_db()
apply_global_styles()

st.header("🥬 재료 관리")

CATEGORIES = ["채소", "과일", "육류", "해산물", "유제품", "양념/소스", "곡류/면", "음료", "냉동식품", "기타"]

# --- 유통기한 임박 경고 ---
expiring = get_expiring_ingredients(days=3)
if expiring:
    st.markdown(f"""
    <div style="background:#fff5f5; border-radius:12px; padding:0.8rem 1rem; margin-bottom:1rem;
                font-family:'Noto Sans KR',sans-serif;">
        <span style="font-weight:600; color:#e53e3e;">⚠️ 유통기한 임박 재료 {len(expiring)}개</span>
    </div>
    """, unsafe_allow_html=True)
    for ing in expiring:
        days_left = (datetime.strptime(ing.expiry_date, "%Y-%m-%d").date() - date.today()).days
        if days_left < 0:
            label = f"**{ing.name}** — 유통기한 {abs(days_left)}일 지남"
        elif days_left == 0:
            label = f"**{ing.name}** — 오늘까지"
        else:
            label = f"**{ing.name}** — {days_left}일 남음"
        st.caption(label)
    st.markdown("---")

# --- 재료 추가 폼 ---
st.subheader("재료 추가")
with st.form("add_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("재료명", placeholder="예: 당근")
    with col2:
        category = st.selectbox("카테고리", CATEGORIES)

    col3, col4 = st.columns([1, 1])
    with col3:
        quantity = st.text_input("수량", placeholder="예: 3개")
    with col4:
        expiry = st.date_input("유통기한 (선택)", value=None, min_value=date.today())

    submitted = st.form_submit_button("추가", use_container_width=True)
    if submitted and name.strip():
        exp_str = expiry.isoformat() if expiry else None
        add_ingredient(name.strip(), category, quantity.strip() or None, exp_str)
        st.success(f"'{name.strip()}' 추가 완료!")
        st.rerun()

# --- 재료 목록 ---
st.subheader("보유 재료 목록")

ingredients = get_all_ingredients()

if not ingredients:
    st.info("등록된 재료가 없습니다. 위에서 재료를 추가하거나 '냉장고 스캔' 페이지를 이용해보세요.")
else:
    all_cats = sorted(set(ing.category for ing in ingredients))
    selected_cat = st.selectbox("카테고리 필터", ["전체"] + all_cats, label_visibility="collapsed")

    filtered = ingredients if selected_cat == "전체" else [i for i in ingredients if i.category == selected_cat]

    for ing in filtered:
        # 유통기한 표시
        expiry_display = "-"
        expiry_color = ""
        if ing.expiry_date:
            try:
                exp_date = datetime.strptime(ing.expiry_date, "%Y-%m-%d").date()
                days_left = (exp_date - date.today()).days
                expiry_display = ing.expiry_date
                if days_left < 0:
                    expiry_color = "color:#e53e3e; font-weight:600;"
                    expiry_display += " (만료)"
                elif days_left <= 3:
                    expiry_color = "color:#e6a700; font-weight:600;"
                    expiry_display += f" ({days_left}일)"
            except ValueError:
                expiry_display = ing.expiry_date

        # 재료 정보 (1행)
        exp_html = ""
        if expiry_color:
            exp_html = f" · <span style='{expiry_color}'>{expiry_display}</span>"
        else:
            exp_html = f" · {expiry_display}" if expiry_display != "-" else ""

        st.markdown(
            f"**{ing.name}** · {ing.category} · {ing.quantity or '-'}{exp_html}",
            unsafe_allow_html=True,
        )

        # 버튼 (2행)
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("수정", key=f"edit_{ing.id}", use_container_width=True):
                st.session_state[f"editing_{ing.id}"] = True
        with btn2:
            if st.button("삭제", key=f"del_{ing.id}", use_container_width=True):
                delete_ingredient(ing.id)
                st.rerun()

        # 수정 모드
        if st.session_state.get(f"editing_{ing.id}", False):
            with st.form(f"edit_form_{ing.id}"):
                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    new_name = st.text_input("재료명", value=ing.name, key=f"ename_{ing.id}")
                with ec2:
                    new_cat = st.selectbox(
                        "카테고리", CATEGORIES,
                        index=CATEGORIES.index(ing.category) if ing.category in CATEGORIES else len(CATEGORIES) - 1,
                        key=f"ecat_{ing.id}",
                    )
                ec3, ec4 = st.columns([1, 1])
                with ec3:
                    new_qty = st.text_input("수량", value=ing.quantity or "", key=f"eqty_{ing.id}")
                with ec4:
                    current_exp = None
                    if ing.expiry_date:
                        try:
                            current_exp = datetime.strptime(ing.expiry_date, "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    new_exp = st.date_input("유통기한", value=current_exp, key=f"eexp_{ing.id}")

                ecol1, ecol2 = st.columns(2)
                with ecol1:
                    if st.form_submit_button("저장", use_container_width=True):
                        exp_str = new_exp.isoformat() if new_exp else None
                        update_ingredient(ing.id, name=new_name.strip(), category=new_cat,
                                          quantity=new_qty.strip() or None, expiry_date=exp_str)
                        st.session_state[f"editing_{ing.id}"] = False
                        st.rerun()
                with ecol2:
                    if st.form_submit_button("취소", use_container_width=True):
                        st.session_state[f"editing_{ing.id}"] = False
                        st.rerun()

    st.markdown("---")
    st.caption(f"총 {len(filtered)}개 재료 (전체 {len(ingredients)}개)")

    with st.expander("위험 구역"):
        if st.button("모든 재료 삭제", type="primary"):
            clear_all()
            st.rerun()
