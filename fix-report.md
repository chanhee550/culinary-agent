# UI 버그 수정 보고서

**날짜:** 2026-04-07  
**작업:** 디자인 개선 후 발생한 렌더링 버그 전체 점검 및 수정

---

## 발견된 문제 및 수정 내용

### 1. styles.py — 아이콘 폰트 깨짐 (치명적)

- **증상:** Expander 화살표가 `arrow_right` 텍스트로 표시, Selectbox 드롭다운 아이콘 깨짐
- **원인:** `*` (전체 선택자)에 `font-family`를 `!important`로 적용하여 Streamlit 내부 Material Icons 폰트가 덮어씌워짐
- **수정:** `*` 대신 `html, body, h1~h6, p, span, div, input, button` 등 텍스트 요소만 명시적으로 지정하여 아이콘 폰트 보존

### 2. styles.py — 슬라이더 CSS 셀렉터 과범위

- **증상:** 슬라이더 트랙/핸들/배경이 모두 같은 색상으로 표시될 수 있음
- **원인:** `div[data-testid="stSlider"] > div > div > div`가 너무 광범위
- **수정:** `[data-testid="stThumbValue"]`로 변경하여 값 텍스트만 색상 적용

### 3. 2_ingredients.py — HTML/Streamlit 위젯 레이아웃 불일치

- **증상:** HTML 카드와 수정/삭제 버튼이 시각적으로 분리되어 어색한 레이아웃
- **원인:** `st.markdown(unsafe_allow_html=True)`로 만든 카드와 `st.button`이 별도 블록으로 렌더링
- **수정:** HTML 카드를 제거하고 Streamlit 네이티브 `st.columns` 5열 레이아웃으로 통일

### 4. app.py, 1_fridge_scan.py, 3_recipes.py — inline HTML 폰트 미적용

- **증상:** `st.markdown(unsafe_allow_html=True)`로 삽입된 HTML 블록에 커스텀 폰트가 적용되지 않을 수 있음
- **원인:** CSS 셀렉터 범위 축소로 inline HTML `<div>`에 폰트 상속이 보장되지 않음
- **수정:** 모든 inline HTML 루트 요소에 `font-family:'Noto Sans KR',sans-serif` 명시

---

## 수정된 파일 목록

| 파일 | 수정 내용 |
|------|-----------|
| `styles.py` | 폰트 셀렉터 축소 (아이콘 보존), 슬라이더 셀렉터 수정 |
| `app.py` | 메인 카드 HTML에 font-family 추가 |
| `pages/1_fridge_scan.py` | 감지 결과 배너 HTML에 font-family 추가 |
| `pages/2_ingredients.py` | HTML 카드 제거 → Streamlit 네이티브 columns 레이아웃으로 교체 |
| `pages/3_recipes.py` | 태그, 뱃지, 재료 목록 HTML에 font-family 추가 |
