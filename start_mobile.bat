@echo off
REM O'CHEF — Mobile (FastAPI :8001 + Next.js :3000)
title O'CHEF
cd /d "%~dp0"

echo.
echo  =================================
echo   오셰 (O'CHEF) - Mobile
echo  =================================
echo.

REM 1) Backend on :8001 (faster-whisper + edge-tts + Claude)
start "Backend (FastAPI :8001)" cmd /k py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8001

REM 2) Mobile PWA dev server on :3000
start "Mobile (Next.js :3000)" cmd /k "cd mobile && npm run dev"

REM 3) 두 서버가 살아날 때까지 대기 (최대 90초)
echo.
echo   서버 준비 대기 중... (백엔드 + Next dev 부팅, 보통 15~25초)
powershell -NoProfile -Command ^
  "$ok=$false; for($i=0;$i -lt 45;$i++){ try { $b=(Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8001/health).StatusCode; $m=(Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:3000).StatusCode; if($b -eq 200 -and $m -eq 200){ $ok=$true; break } } catch {} Start-Sleep -Seconds 2 } ; if(-not $ok){ Write-Host '   (timeout - 두 창의 로그를 확인하세요)' -ForegroundColor Yellow }"

start "" http://localhost:3000

echo.
echo  Backend  : http://localhost:8001/health
echo  Mobile   : http://localhost:3000
echo.
echo  종료하려면 위에 새로 뜬 두 cmd 창을 닫으세요.
pause
