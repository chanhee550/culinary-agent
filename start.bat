@echo off
title O'CHEF
cd /d "%~dp0"
echo.
echo  =============================
echo   오셰 (O'CHEF) 실행 중...
echo  =============================
echo.
start "" http://localhost:8501
streamlit run app.py --server.headless true
pause
