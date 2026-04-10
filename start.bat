@echo off
title Culinary Agent
cd /d "%~dp0"
echo.
echo  =============================
echo   Culinary Agent 실행 중...
echo  =============================
echo.
start "" http://localhost:8501
streamlit run app.py --server.headless true
pause
