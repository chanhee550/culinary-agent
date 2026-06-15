# 오셰 (O'CHEF)

냉장고 속 재료를 관리하고, Claude 기반 AI로 맞춤 레시피를 추천받는 음성 요리 도우미입니다. ASR · LLM · TTS 풀체인이 한국어로 동작합니다.

현재 프로젝트는 세 가지 실행 표면을 함께 갖고 있습니다.

- **Streamlit 웹 앱**: 로컬/프로토타입용 메인 UI
- **FastAPI 백엔드**: 모바일 PWA가 호출하는 HTTP API
- **Next.js 모바일 PWA**: 모바일 우선 UI, 추후 Android TWA 배포 가능

---

## 주요 기능

### 1. 냉장고 스캔

- 냉장고 사진 여러 장 업로드
- Claude Vision으로 재료 자동 인식
- 확실한 재료(`confirmed`)와 통/병/반찬처럼 불확실한 항목(`unknowns`) 분리
- 사용자가 확인/수정한 뒤 선택 저장
- 같은 이름의 재료는 중복 생성 대신 업데이트

### 2. 재료 관리

- 재료 수동 추가/수정/삭제
- 카테고리별 분류
- 수량과 유통기한 관리
- 유통기한 임박 재료 경고

### 3. 레시피 추천

- 보유 재료 기반 Claude 레시피 추천
- 허용할 부족 재료 개수 조절
- 사용자 프로필 반영
  - 요리 숙련도
  - 선호 요리 종류
  - 맛 선호
  - 알레르기 제외
- 유통기한 임박 재료 우선 활용
- 부족 재료 중 대체 가능한 항목 자동 안내

### 4. 저장 레시피

- 마음에 드는 추천 레시피 저장
- 저장한 레시피 다시 보기
- 별점 평가
- 삭제

### 5. 장보기 목록

- 부족 재료를 레시피에서 장보기 목록으로 추가
- 수동 항목 추가
- 구매 필요/구매 완료 체크
- 완료 항목 일괄 삭제

### 6. 오늘의 레시피

- 보유 재료 기반으로 오늘의 추천 레시피 3개 생성
- 날짜별 캐시 저장
- 최근 캐시 자동 정리

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Streamlit UI | Streamlit |
| Mobile UI | Next.js 14, React, Tailwind CSS, next-pwa |
| Backend API | FastAPI, Uvicorn |
| AI | Anthropic Claude API |
| Vision | Claude Vision + Pillow 이미지 전처리 |
| ASR | OpenAI Whisper |
| TTS | edge-tts, Microsoft Edge online voices |
| DB | SQLite 기본, Firestore 일부 지원 |
| 테스트 | Playwright + axe-core 접근성 테스트 |

---

## 프로젝트 구조

```text
culinary-agent/
├── app.py                         # Streamlit 메인 페이지
├── i18n.py                        # Streamlit 메인 페이지 중심 한/영 번역
├── styles.py                      # Streamlit 전역 스타일
├── requirements.txt               # Streamlit/AI 공통 Python 의존성
├── .env.example                   # 환경변수 예시
│
├── pages/                         # Streamlit 세부 페이지
│   ├── 1_📷_냉장고 스캔.py
│   ├── 2_🥬_재료 관리.py
│   ├── 3_🍽️_레시피 추천.py
│   ├── 4_👤_프로필 설정.py
│   ├── 5_📚_저장 레시피.py
│   └── 6_🛒_장보기 목록.py
│
├── services/
│   ├── vision.py                  # 이미지 분석
│   ├── recipe.py                  # 레시피 추천
│   └── substitution.py            # 대체 재료 매칭
│
├── db/
│   ├── database.py                # SQLite 연결/스키마
│   ├── models.py                  # dataclass 모델
│   ├── repository.py              # SQLite CRUD
│   ├── storage.py                 # 저장소 선택기
│   └── firestore_repo.py          # Firestore 재료 저장소 일부 구현
│
├── backend/
│   ├── main.py                    # FastAPI 앱
│   └── requirements.txt           # API 서버 추가 의존성
│
├── mobile/                        # Next.js PWA
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── public/
│
├── ax-tests/                      # 접근성 자동 테스트
├── android/                       # Android TWA 빌드 가이드
└── data/
    ├── substitutions.json         # 대체 재료 데이터
    └── culinary.db                # SQLite DB, 런타임 생성
```

---

## 환경변수

`.env.example`을 참고해 `.env`를 만듭니다.

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

VISION_MODEL=claude-sonnet-4-6
RECIPE_MODEL=claude-haiku-4-5-20251001
OPENAI_TRANSCRIBE_MODEL=whisper-1
EDGE_TTS_VOICE=ko-KR-SunHiNeural

STORAGE_BACKEND=sqlite
```

주요 변수:

- `ANTHROPIC_API_KEY`: Claude API 키
- `OPENAI_API_KEY`: OpenAI 음성 전사 API 키
- `VISION_MODEL`: 냉장고 사진 분석 모델
- `RECIPE_MODEL`: 레시피 생성 모델
- `OPENAI_TRANSCRIBE_MODEL`: 음성 명령 전사 모델, 기본값 `whisper-1`
- `EDGE_TTS_VOICE`: 짧은 음성 응답에 사용할 edge-tts 한국어 음성
- `STORAGE_BACKEND`: `sqlite` 또는 `firestore`

> 현재 Firestore 모드는 재료 저장소 일부만 구현되어 있습니다. 저장 레시피, 장보기, 프로필 등은 SQLite repository를 직접 사용합니다.

---

## 실행 방법

### 1. Streamlit 앱

```bash
pip install -r requirements.txt
streamlit run app.py
```

접속:

```text
http://localhost:8501
```

### 2. FastAPI 백엔드

모바일 PWA를 실행하려면 백엔드가 먼저 떠 있어야 합니다.

```bash
pip install -r requirements.txt -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

헬스 체크:

```text
http://localhost:8000/health
```

### 3. Next.js 모바일 PWA

```bash
cd mobile
npm install
npm run dev
```

접속:

```text
http://localhost:3000
```

기본 API 주소는 `http://localhost:8000`입니다. 다른 백엔드를 쓰려면 `mobile/.env.local`에 설정합니다.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

또는 배포 환경에서는 `BACKEND_URL`을 설정하면 Next.js rewrite로 `/api/*` 프록시를 구성할 수 있습니다.

---

## API 개요

FastAPI는 모바일 앱을 위한 HTTP 엔드포인트를 제공합니다.

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/scan` | 이미지 여러 장 분석 |
| GET | `/ingredients` | 재료 목록 |
| POST | `/ingredients` | 재료 추가 |
| POST | `/ingredients/bulk` | 스캔 결과 일괄 저장 |
| PATCH | `/ingredients/{id}` | 재료 수정 |
| DELETE | `/ingredients/{id}` | 재료 삭제 |
| DELETE | `/ingredients` | 모든 재료 삭제 |
| POST | `/recipes` | 레시피 추천 |
| POST | `/voice/command` | 짧은 음성 명령 전사 및 조리 액션/응답문 변환 |
| POST | `/voice/tts` | 짧은 확인 문장을 TTS mp3로 변환 |
| GET | `/saved_recipes` | 저장 레시피 목록 |
| POST | `/saved_recipes` | 레시피 저장 |
| PATCH | `/saved_recipes/{id}/rating` | 별점 수정 |
| DELETE | `/saved_recipes/{id}` | 저장 레시피 삭제 |
| GET | `/shopping` | 장보기 목록 |
| POST | `/shopping` | 장보기 항목 추가 |
| PATCH | `/shopping/{id}/toggle` | 구매 완료 토글 |
| DELETE | `/shopping/{id}` | 장보기 항목 삭제 |
| DELETE | `/shopping/checked/all` | 완료 항목 일괄 삭제 |
| POST | `/shopping/from_missing` | 부족 재료를 장보기로 추가 |

---

## 접근성 테스트

Streamlit 앱을 대상으로 axe-core 기반 접근성 테스트를 실행할 수 있습니다.

```bash
cd ax-tests
npm install
npm test
```

리포트까지 생성:

```bash
npm run test:report
```

테스트 대상 기본 주소는 `http://localhost:8501`입니다.

---

## Android 배포

`mobile/` PWA를 배포한 뒤 Bubblewrap으로 Android TWA 앱 번들을 만들 수 있습니다.

자세한 절차는 [android/README.md](android/README.md)를 참고하세요.

---

## 현재 구현 상태와 주의점

- Streamlit 앱은 전체 핵심 흐름이 구현되어 있습니다.
- 모바일 PWA는 FastAPI를 통해 스캔, 재료, 레시피, 저장 레시피, 장보기 기능을 제공합니다.
- 모바일 레시피 상세 화면은 OpenAI Whisper 기반 음성 명령과 edge-tts 기반 짧은 확인 음성을 지원합니다.
- `i18n.py`는 준비되어 있지만, Streamlit 개별 페이지의 다국어 적용은 아직 부분적입니다.
- Firestore 저장소는 재료 관리 일부에만 연결되어 있습니다.
- 모바일 재료 관리 화면은 현재 수량/카테고리 중심이며, Streamlit의 유통기한 UI와 완전히 동일하지 않습니다.
- Claude 호출이 필요한 기능은 `.env`의 `ANTHROPIC_API_KEY`가 있어야 동작합니다.
- 음성 명령 기능은 `.env`의 `OPENAI_API_KEY`가 있어야 동작합니다.
- TTS는 무료 `edge-tts`를 사용하지만 Microsoft Edge online voices에 접속하므로 백엔드 서버의 네트워크 연결이 필요합니다.
