# 오셰 (O'CHEF) — Mobile PWA

Next.js 14 App Router 기반 모바일 우선 PWA입니다. 루트의 FastAPI 백엔드(`backend/main.py`)를 호출해 재료 관리, 냉장고 스캔, 레시피 추천, 저장 레시피, 장보기 목록을 제공합니다.

---

## 사전 준비

- Node.js 20+
- Python 백엔드 실행
- Claude 기능을 쓰려면 루트 `.env`에 `ANTHROPIC_API_KEY` 설정
- 음성 명령을 쓰려면 루트 `.env`에 `OPENAI_API_KEY` 설정
- 짧은 TTS 확인 응답은 무료 `edge-tts`를 사용하며 백엔드 네트워크 연결이 필요

백엔드 실행:

```bash
cd ..
pip install -r requirements.txt -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 개발 서버 실행

```bash
cd mobile
npm install
npm run dev
```

접속:

```text
http://localhost:3000
```

기본 API 주소:

```text
http://localhost:8000
```

다른 API 주소를 쓰려면 `mobile/.env.local`을 만듭니다.

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 빌드

```bash
npm run build
npm start
```

---

## 주요 화면

| 경로 | 기능 |
|------|------|
| `/` | 홈, 보유 재료 요약, 빠른 이동 |
| `/scan` | 사진 촬영/업로드, AI 재료 인식, 결과 저장 |
| `/ingredients` | 재료 추가/수정/삭제, 카테고리 필터 |
| `/recipes` | AI 레시피 추천, 레시피 저장, 부족 재료 처리 |
| `/saved` | 저장 레시피 조회, 별점, 삭제 |
| `/shopping` | 장보기 목록 추가/체크/삭제 |

---

## 디렉터리 구조

```text
mobile/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── scan/page.tsx
│   ├── ingredients/page.tsx
│   ├── recipes/page.tsx
│   ├── saved/page.tsx
│   └── shopping/page.tsx
│
├── components/
│   └── BottomNav.tsx
│
├── lib/
│   ├── api.ts                    # FastAPI 클라이언트
│   └── types.ts                  # 공유 타입
│
├── public/
│   ├── manifest.json             # PWA manifest
│   └── icons/                    # PWA 아이콘 위치
│
├── next.config.mjs               # next-pwa + rewrite 설정
├── tailwind.config.ts
└── package.json
```

---

## API 연결

`lib/api.ts`는 기본적으로 `NEXT_PUBLIC_API_URL`을 사용하고, 값이 없으면 `http://localhost:8000`으로 요청합니다.

배포 환경에서 같은 도메인 프록시를 쓰려면 `next.config.mjs`의 rewrite를 활용할 수 있습니다.

```env
BACKEND_URL=https://your-backend.example.com
```

이 경우 `/api/:path*` 요청을 백엔드로 프록시하도록 구성되어 있습니다. 단, 현재 `lib/api.ts`의 기본값은 직접 `http://localhost:8000`을 향하므로, 배포 전략에 맞춰 `NEXT_PUBLIC_API_URL` 또는 API 경로 정책을 함께 맞춰야 합니다.

---

## 음성 조리 가이드

`/recipes`의 레시피 상세 화면에서는 단계별 조리법 카드와 음성 명령 버튼을 제공합니다.

지원하는 기본 명령:

- "다음 단계"
- "이전 단계"
- "다시 읽어줘"
- "전체 보기"
- "재료 알려줘"
- "타이머 5분"

브라우저에서 녹음한 오디오는 FastAPI의 `/voice/command`로 전송되고, 백엔드가 OpenAI 음성 전사 API(`OPENAI_TRANSCRIBE_MODEL`, 기본 `whisper-1`)로 텍스트를 얻은 뒤 조리 액션과 짧은 응답문으로 변환합니다.

그 뒤 모바일 앱은 `/voice/tts`를 호출해 응답문만 mp3로 재생합니다. 레시피 전체를 읽지 않고, 사용자의 요청을 확인하는 짧은 문장만 읽습니다.

예:

- 사용자: "5분 타이머 맞춰줘"
- TTS: "5분 타이머를 설정하겠습니다."

---

## PWA / Android TWA

PWA manifest는 `public/manifest.json`에 있습니다.

Android TWA로 Play Store 배포를 진행하려면 루트의 [android/README.md](../android/README.md)를 참고하세요.

필수 후속 작업:

- 실제 192x192, 512x512 PNG 아이콘 추가
- HTTPS 도메인에 PWA 배포
- Bubblewrap으로 TWA 프로젝트 생성
- `.well-known/assetlinks.json`에 SHA-256 fingerprint 등록

---

## 현재 제한 사항

- 모바일 재료 관리 화면은 Streamlit보다 단순하며, 유통기한 입력/경고 UI는 아직 온전히 반영되어 있지 않습니다.
- 프로필 설정 화면은 현재 모바일 PWA에 없습니다. 레시피 추천의 프로필 반영은 백엔드/SQLite에 저장된 값을 사용합니다.
- Claude 호출 기능은 백엔드의 `ANTHROPIC_API_KEY` 설정이 필요합니다.
- 음성 명령 기능은 백엔드의 `OPENAI_API_KEY` 설정이 필요합니다.
- TTS는 `edge-tts` 기반이라 별도 유료 API 키는 없지만, Microsoft Edge online voices 네트워크 호출이 필요합니다.
