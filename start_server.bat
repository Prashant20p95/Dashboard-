@echo off
title OpsCommand — Operations & Logistics Command Portal Server
cd /d "%~dp0"
echo ========================================================
echo   OpsCommand Operations & Logistics Portal (Port 8000)
echo   URL: http://127.0.0.1:8000
echo ========================================================
echo Starting server on http://127.0.0.1:8000 ...
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
