# Culinary Agent

냉장고 속 재료를 관리하고, AI 기반으로 맞춤 레시피를 추천받는 웹 애플리케이션입니다.

## 주요 기능

### 1. 냉장고 스캔
- 냉장고 사진을 업로드하면 Claude Vision AI가 재료를 자동 인식
- 여러 장의 사진 동시 업로드 가능
- 감지된 재료를 체크리스트로 확인 후 선택 저장
- 중복 재료 자동 처리 (이미 있는 재료는 업데이트)

### 2. 재료 관리
- 재료 수동 추가/수정/삭제
- 카테고리별 분류 (채소, 육류, 양념/소스, 해산물 등 10개 카테고리)
- 수량 관리
- 카테고리별 필터링

### 3. 레시피 추천
- 보유 재료 기반 AI 레시피 추천 (3~5개)
- 부족 재료 허용 개수 조절 가능 (기본 2개)
- 재료별 색상 코딩: 🟢보유 / 🟡대체가능 / 🔴부족
- 상세 조리법, 난이도, 예상 조리시간 제공

### 4. 대체 재료 안내
- 20개 이상의 한식 소스/양념 대체 레시피 내장
- 예: 참소스 → 간장+식초+설탕+물, 굴소스 → 간장+설탕+참치액
- 레시피 추천 시 대체 가능한 재료 자동 표시
- 비율과 사용법 안내 포함

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| UI | Streamlit |
| AI | Claude API (anthropic SDK) - Vision + Text |
| DB | SQLite |
| 언어 | Python 3.10+ |

---

## 프로젝트 구조

```
culinary-agent/
├── app.py                     # Streamlit 진입점 (메인 페이지)
├── requirements.txt           # 의존성 패키지
├── .env                       # API 키 설정
│
├── db/
│   ├── database.py            # SQLite 연결 및 테이블 초기화
│   ├── models.py              # 데이터 모델 (Ingredient dataclass)
│   └── repository.py          # CRUD 함수 (추가/수정/삭제/조회)
│
├── services/
│   ├── vision.py              # Claude Vision API - 이미지→재료 감지
│   ├── recipe.py              # Claude API - 재료→레시피 추천
│   └── substitution.py        # 대체 재료 검색 및 매칭 로직
│
├── pages/
│   ├── 1_fridge_scan.py       # 냉장고 스캔 페이지
│   ├── 2_ingredients.py       # 재료 관리 페이지
│   └── 3_recipes.py           # 레시피 추천 페이지
│
└── data/
    ├── substitutions.json     # 대체 재료 매핑 데이터 (20개+)
    └── culinary.db            # SQLite DB (런타임 자동 생성)
```

---

## 설치 및 실행

### 1. 의존성 설치
```bash
cd culinary-agent
pip install -r requirements.txt
```

### 2. API 키 설정
`.env` 파일을 열어 Anthropic API 키를 입력합니다:
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 3. 실행
```bash
streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 접속합니다.

---

## 개발 과정

### Phase 1: 프로젝트 기반 구축
- 프로젝트 디렉토리 구조 생성
- `requirements.txt`, `.env` 설정
- SQLite 데이터베이스 레이어 구현 (`database.py`, `models.py`, `repository.py`)
- `Ingredient` 모델: id, name(UNIQUE), category, quantity, added_at, source
- UPSERT 전략으로 중복 재료 자동 처리
- Streamlit 메인 페이지(`app.py`) 및 재료 관리 페이지(`2_ingredients.py`) 구현
- 재료 추가/수정/삭제/필터 CRUD UI 완성

### Phase 2: 냉장고 스캔 (Claude Vision 연동)
- `services/vision.py`: Claude Vision API를 통한 이미지 분석
- 여러 이미지 동시 처리 및 재료 중복 제거 로직
- `pages/1_fridge_scan.py`: 이미지 업로드 → 스캔 → 체크리스트 → 저장 UI
- **코드 리뷰 후 버그 수정:**
  - `repository.py`: ON CONFLICT 시 `lastrowid`가 0 반환되는 버그 → name 기반 조회로 수정
  - `vision.py`: LLM 응답 JSON 파싱 강화 (정규식 추출 방식으로 변경)
  - `vision.py`: 개별 이미지 분석 실패 시 전체 실패 방지 (try/except 추가)

### Phase 3: 대체 재료 시스템
- `data/substitutions.json`: 20개 한식 소스/양념 대체 레시피 데이터 구축
  - 참소스, 굴소스, 미림, 쌈장, 데리야끼소스 등
  - 각 항목에 구성 재료, 비율, 사용법 포함
- `services/substitution.py`: 대체 가능 여부 판별 및 대체법 텍스트 생성 로직

### Phase 4: 레시피 추천 (Claude API 연동)
- `services/recipe.py`: 보유 재료 + 대체 재료 정보를 포함한 프롬프트로 Claude에 레시피 요청
- 레시피별 부족 재료에 대해 대체 가능 여부 자동 보강
- `pages/3_recipes.py`: 레시피 카드 UI
  - 색상 코딩된 재료 목록 (보유/대체가능/부족)
  - 접기/펼치기 형태의 상세 조리법
  - 난이도, 조리시간 표시

### Phase 5: 테스트 및 마무리
- 전체 코드 리뷰 및 버그 수정
- README.md 문서화

---

## 주요 설계 결정

| 결정 | 이유 |
|------|------|
| Streamlit 선택 | Python만으로 빠른 프로토타이핑, 이미지 업로드/데이터 편집 내장 |
| SQLite 선택 | 재료 중복 체크에 SQL UNIQUE 제약 활용, Python 기본 내장 |
| JSON 파싱에 정규식 사용 | LLM 응답이 마크다운 펜스나 부가 텍스트를 포함할 수 있어 견고한 파싱 필요 |
| 대체 재료를 JSON 파일로 관리 | 정적 참조 데이터로 별도 DB 불필요, 수동 확장 용이 |
| 레시피 비저장 | 매번 현재 재료 기반으로 동적 생성, 즐겨찾기는 추후 확장 가능 |
