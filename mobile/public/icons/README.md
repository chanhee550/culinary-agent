# 앱 아이콘 만들기

이 폴더에는 다음 두 파일이 **반드시** 있어야 합니다 (PWA 설치·TWA 빌드 필수):

```
icons/
├── icon-192.png    192×192px, PNG, 알파 채널 OK
└── icon-512.png    512×512px, PNG, 알파 채널 OK
```

## 빠르게 만드는 방법

### 1. Figma / Canva 등에서 직접 디자인
- 안전 영역(Safe area) 고려: 가장자리 10% 안쪽에 핵심 그래픽 배치
- maskable 대응: 정사각형이지만 원형으로 잘릴 수도 있다고 가정

### 2. 무료 생성기 사용
- [Maskable.app Editor](https://maskable.app/editor) — 단일 이미지 → maskable 아이콘 생성
- [PWA Asset Generator](https://www.npmjs.com/package/pwa-asset-generator):
  ```bash
  npx pwa-asset-generator logo.png ./mobile/public/icons \
      --icon-only --opaque false --maskable
  ```

### 3. 임시 플레이스홀더 (V0 테스트용)
빠르게 빌드만 돌려보고 싶다면 [favicon.io/emoji-favicons](https://favicon.io/emoji-favicons/cooking)에서
🍳 이모지 아이콘을 받아 192×192, 512×512로 리사이즈하세요.

## 추가로 권장되는 아이콘 (Play Store 등록 시 필요)

이 폴더가 아니라 Play Console에 별도 업로드:
- **Play Store 아이콘**: 512×512 PNG (32-bit, 알파 OK)
- **Feature Graphic**: 1024×500 PNG (스토어 상단 배너)
- **스크린샷**: 1080×1920 (휴대폰), 최소 2장 / 최대 8장
