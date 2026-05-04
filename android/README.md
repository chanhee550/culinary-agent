# Android TWA 빌드 가이드

PWA(`mobile/`)를 **TWA(Trusted Web Activity)** 로 래핑하여 Play Store에 올릴 수 있는
AAB(Android App Bundle)를 생성합니다.

## 사전 조건

1. **PWA가 HTTPS 도메인에 배포되어 있어야 합니다** (예: `https://culinary-agent.app`)
   - Vercel 무료 도메인(`xxx.vercel.app`)도 OK
   - `https://<domain>/manifest.json`이 200으로 응답해야 함

2. **JDK 17+** 설치
   ```bash
   java -version   # 17 이상이어야 함
   ```

3. **Android SDK** — Android Studio 설치 시 함께 설치됨
   ```bash
   # 또는 cmdline-tools만 설치하고 환경변수 ANDROID_HOME 설정
   ```

4. **Bubblewrap CLI**
   ```bash
   npm install -g @bubblewrap/cli
   ```

## 1단계 — TWA 프로젝트 초기화

```bash
cd android
bubblewrap init --manifest=https://YOUR-DOMAIN.com/manifest.json
```

대화형으로 묻는 항목:

| 질문 | 권장 값 | 비고 |
|------|---------|------|
| Domain | `culinary-agent.app` (배포 도메인) | manifest의 host와 일치 |
| URL of the manifest | (자동) | |
| Application ID | `com.chanhee550.culinaryagent` | **한 번 정하면 변경 불가** |
| Application name | `Culinary Agent` | |
| Display mode | `standalone` | |
| Status bar color | `#10b981` | manifest의 theme_color와 일치 |
| Splash color | `#ffffff` | manifest의 background_color |
| Icon | `https://YOUR-DOMAIN/icons/icon-512.png` | URL로 참조 |
| Maskable icon | (옵션) | |
| Notification icon | (옵션) | |
| Signing key info | 새로 생성 | 패스워드 안전하게 보관!! |

## 2단계 — 서명 키(Keystore) 백업 ⚠️

`android.keystore` 파일과 패스워드를 **반드시 안전한 곳에 백업**하세요.
이걸 잃어버리면 앱 업데이트가 영영 불가능합니다.

추천 백업 위치:
- 1Password / Bitwarden 같은 비밀번호 관리자 (파일 첨부)
- 암호화된 USB 드라이브
- **GitHub에 커밋하지 마세요!** (`.gitignore`에 이미 차단됨)

## 3단계 — AAB 빌드

```bash
bubblewrap build
```

생성물:
- `app-release-bundle.aab` ← Play Console에 업로드할 파일
- `app-release-signed.apk` ← (옵션) 사이드로드 테스트용

빌드 중 출력되는 **SHA-256 fingerprint** 를 메모해두세요:
```
SHA-256 fingerprint: AA:BB:CC:DD:EE:FF:...
```

## 4단계 — Digital Asset Links 등록 ⭐ 매우 중요

이걸 안 하면 앱 실행 시 상단에 URL 바("이 페이지는 chrome.com에서 제공")가 떠서 안 예쁩니다.

### 4-1. assetlinks.json 갱신

[mobile/public/.well-known/assetlinks.json](../mobile/public/.well-known/assetlinks.json) 의
`REPLACE_WITH_SHA256_FROM_BUBBLEWRAP_BUILD` 부분을 위에서 메모한 SHA-256으로 교체하세요.

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.chanhee550.culinaryagent",
    "sha256_cert_fingerprints": ["AA:BB:CC:DD:EE:FF:..."]
  }
}]
```

### 4-2. PWA 재배포

```bash
cd ../mobile
git add public/.well-known/assetlinks.json
git commit -m "chore: add asset links for TWA"
git push  # Vercel이 자동 재배포
```

### 4-3. 검증

```bash
curl https://YOUR-DOMAIN.com/.well-known/assetlinks.json
# → 위에 작성한 JSON이 그대로 반환되어야 함
```

또는 [Statement List Tester](https://developers.google.com/digital-asset-links/tools/generator) 로 검증.

## 5단계 — Play Console 업로드

[Google Play Console](https://play.google.com/console) → 앱 만들기 → 출시 → 테스트 → 내부 테스트:

1. `app-release-bundle.aab` 업로드
2. 출시 노트 작성
3. 테스터 이메일 추가 (본인 Gmail부터)
4. 검토 → 출시 시작

자세한 Play Console 절차는 루트 [README.md](../README.md#play-store-배포-절차) 참조.

## 흔한 오류

| 증상 | 원인 / 해결 |
|------|-------------|
| 앱 실행 시 상단에 URL 바 노출 | assetlinks.json 미등록 또는 SHA-256 불일치 |
| `bubblewrap init` 실패 | Java 버전 확인 (JDK 17+) |
| `Could not find tools.jar` | `JAVA_HOME` 환경변수 설정 |
| 빌드 시 SDK 누락 에러 | Android Studio에서 SDK Manager → 누락 SDK 다운로드 |
| AAB 업로드 시 "버전 코드 충돌" | `twa-manifest.json`의 `appVersionCode`를 +1 |
| 흰 화면만 뜸 | manifest.json의 `start_url`이 200으로 응답하는지 확인 |

## 업데이트 빌드

코드 수정 후 새 버전 빌드:

```bash
# 버전 번호 올리기
# twa-manifest.json:
#   "appVersionCode": 2,
#   "appVersionName": "0.1.1"

bubblewrap update    # twa-manifest.json 변경사항 반영
bubblewrap build     # 새 AAB 생성
```

Play Console에 새 AAB 업로드 → 새 버전 출시.
