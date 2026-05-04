# Culinary Agent — Mobile (PWA)

Next.js 14 App Router 기반 모바일 우선 PWA. Bubblewrap으로 Android TWA(Trusted Web Activity)
패키징을 거쳐 Play Store에 등록합니다.

## 빠른 시작

### 0. 사전 준비
- Node.js 20+
- 백엔드(`backend/main.py`)가 떠 있어야 합니다 (포트 8000)

### 1. 의존성 설치
```bash
cd mobile
npm install
```

### 2. 환경변수
```bash
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000  ← 로컬 개발
```

### 3. 개발 서버
```bash
npm run dev
# http://localhost:3000
```

브라우저에서 모바일 모드로 보려면 DevTools(`F12`) → Toggle Device Toolbar(`Ctrl+Shift+M`) → iPhone/Pixel 선택.

### 4. 프로덕션 빌드
```bash
npm run build
npm start
```

## 폴더 구조

```
mobile/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # 공통 레이아웃 + 하단 네비
│   ├── page.tsx                  # 홈
│   ├── scan/page.tsx             # 냉장고 스캔 (Level 2 UI)
│   ├── ingredients/page.tsx      # 재료 관리
│   └── recipes/page.tsx          # 레시피 추천
├── components/
│   └── BottomNav.tsx             # 4-탭 하단 네비게이션
├── lib/
│   ├── api.ts                    # FastAPI 백엔드 클라이언트
│   └── types.ts                  # 공유 타입
├── public/
│   ├── manifest.json             # PWA manifest (TWA 필수)
│   ├── icons/                    # 192x192, 512x512 PNG (직접 추가)
│   └── .well-known/
│       └── assetlinks.json       # TWA Digital Asset Links (SHA256 교체 필요)
├── next.config.mjs               # next-pwa 설정 + 백엔드 프록시
└── tailwind.config.ts
```

## 모바일 우선 디자인 원칙

- **44px 이상 터치 영역**: 모든 버튼/링크
- **하단 네비**: 엄지로 닿는 영역 (한 손 조작)
- **safe-area-inset**: iOS 노치/홈 인디케이터 대응
- **`maximumScale: 1`**: 입력 시 줌 방지 (font-size: 16px 보장)
- **`capture="environment"`**: 사진 촬영 시 후면 카메라 자동 선택
- **`active:` 의사 클래스**: 터치 피드백 (호버 X)

## 다음 단계 (Play Store 배포)

1. 앱 아이콘을 [public/icons/](./public/icons/)에 추가 (README 참조)
2. PWA를 도메인에 배포 (Vercel 권장):
   ```bash
   npm install -g vercel
   vercel
   ```
3. [android/](../android/) 폴더의 README를 따라 Bubblewrap으로 TWA 빌드
4. AAB를 Google Play Console에 업로드

자세한 절차는 루트 [README.md](../README.md)와 [android/README.md](../android/README.md) 참조.
