# Culinary Agent

냉장고 속 재료를 관리하고, AI 기반으로 맞춤 레시피를 추천받는 웹 애플리케이션입니다.

## 주요 기능

### 1. 냉장고 스캔
- 냉장고 사진을 업로드하면 Claude Vision AI(Haiku 4.5)가 재료를 자동 인식
- 여러 장의 사진을 **병렬로** 동시 분석 (3장 = 1장 분석 시간)
- 결과를 두 그룹으로 분리:
  - **확정 재료**: 모양·라벨로 명확히 식별 가능한 항목 (계란, 우유팩 등) → 체크박스로 선택
  - **불확실 항목**: 통/병에 담긴 음식 → AI가 외관 단서·추측·위치를 제공하고 사용자가 직접 입력
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
| AI | Claude Haiku 4.5 (anthropic SDK) - Vision + Text |
| DB | SQLite (로컬) 또는 Firebase Firestore (클라우드) — 환경변수로 스위칭 |
| 언어 | Python 3.10+ |

---

## 프로젝트 구조 (V0)

```
culinary-agent/
├── app.py                     # Streamlit 데스크톱 앱 (개발/디버깅용으로 유지)
├── requirements.txt
├── .env                       # 공통 환경변수
│
├── services/                  # AI / 비즈니스 로직 (모든 진입점에서 재사용)
│   ├── vision.py              # Claude Haiku 4.5 Vision (confirmed/unknowns 분리)
│   ├── recipe.py              # Claude Haiku 4.5 Text - 한식 레시피
│   └── substitution.py        # 대체 재료 매칭
│
├── db/                        # 저장소 추상화
│   ├── storage.py             # STORAGE_BACKEND 환경변수로 스위칭
│   ├── database.py            # SQLite (로컬)
│   ├── repository.py          # SQLite 구현
│   ├── firestore_repo.py      # Firestore 구현 (멀티 디바이스/유저)
│   └── models.py
│
├── pages/                     # Streamlit 페이지
│   ├── 1_fridge_scan.py
│   ├── 2_ingredients.py
│   └── 3_recipes.py
│
├── backend/                   ⭐ NEW — FastAPI HTTP 백엔드 (모바일 앱이 호출)
│   ├── main.py                # /scan, /ingredients, /recipes 엔드포인트
│   └── requirements.txt
│
├── mobile/                    ⭐ NEW — Next.js PWA 프론트엔드
│   ├── app/                   # 4개 화면 (홈/스캔/재료/레시피)
│   ├── components/            # BottomNav 등
│   ├── lib/                   # API 클라이언트, 타입
│   ├── public/manifest.json   # PWA manifest (TWA 필수)
│   └── public/.well-known/    # assetlinks.json (TWA 도메인 검증용)
│
├── android/                   ⭐ NEW — TWA 빌드 설정/문서
│   └── README.md              # Bubblewrap으로 AAB 만드는 절차
│
└── data/
    ├── substitutions.json
    └── culinary.db            # 런타임 자동 생성
```

---

## 빠른 시작 (V0 — 모바일 앱 동작 확인)

### 터미널 1: 백엔드
```bash
cd culinary-agent
pip install -r requirements.txt -r backend/requirements.txt
cp .env.example .env             # ANTHROPIC_API_KEY 입력
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 터미널 2: 모바일 PWA
```bash
cd culinary-agent/mobile
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# http://localhost:3000
```

### 모바일에서 확인 (같은 Wi-Fi)
1. PC 로컬 IP 확인 (예: 192.168.0.10)
2. 백엔드: `uvicorn ... --host 0.0.0.0`로 떠 있어야 함
3. `mobile/.env.local`을 `NEXT_PUBLIC_API_URL=http://192.168.0.10:8000`으로 변경
4. 폰에서 `http://192.168.0.10:3000` 접속

### Streamlit 데스크톱 앱 (기존, 그대로 사용 가능)
```bash
streamlit run app.py
```

---

## Play Store 배포 절차

V0 → 출시까지 5단계:

1. **PWA 배포** — `mobile/` 디렉토리를 Vercel에 배포 (도메인 확보)
2. **백엔드 배포** — `backend/` 를 Cloud Run / Railway / Fly.io에 배포
3. **앱 아이콘 추가** — [mobile/public/icons/](./mobile/public/icons/) 의 README 참조
4. **TWA 빌드** — [android/README.md](./android/README.md) 절차로 AAB 생성
5. **Play Console 등록** — 개발자 등록($25) → 내부 테스트 → 비공개 테스트(20명, 14일) → 프로덕션

자세한 절차는 [android/README.md](./android/README.md) 참조.

---

## Firestore 사용하기 (선택)

여러 기기 동기화나 Play Store 앱 연동을 염두에 둔다면 Firestore로 전환할 수 있습니다.

### 1. Firebase 프로젝트 준비
1. [Firebase Console](https://console.firebase.google.com)에서 새 프로젝트 생성
2. **Build > Firestore Database** 활성화 (Native 모드, 위치는 `asia-northeast3` 권장)
3. **Project Settings > Service accounts** 탭에서 **Generate new private key** → JSON 파일 다운로드
4. 다운로드한 파일을 프로젝트 루트에 `firebase-service-account.json`으로 저장 (이미 `.gitignore`에 등록됨)

### 2. `.env` 수정
```
STORAGE_BACKEND=firestore
GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json
FIREBASE_USER_ID=local      # 단일 사용자 임시 식별자, Auth 도입 시 실제 uid로 교체
```

### 3. 데이터 스키마
```
/users/{user_id}/ingredients/{auto_id}
    - name: string                (사용자 내 UNIQUE)
    - category: string
    - quantity: string | null
    - source: "scan" | "manual"
    - created_at: timestamp
    - updated_at: timestamp
```

### 4. 백엔드 전환
`STORAGE_BACKEND` 값만 바꾸면 즉시 전환됩니다. 코드 수정 불필요:
- `sqlite` → 로컬 `data/culinary.db`
- `firestore` → 클라우드 Firestore

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
