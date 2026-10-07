@echo off
title PlantHead Web App Controller
cd /d "%~dp0"

echo ======================================================
echo  PlantHead Multi-Device Controller Web App
echo ======================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH!
    pause
    exit /b 1
)

if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

echo [2/3] Activating environment and checking dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [3/3] Starting Web App on http://localhost:8080 ...
start "" http://localhost:8080

python app.py
pause
