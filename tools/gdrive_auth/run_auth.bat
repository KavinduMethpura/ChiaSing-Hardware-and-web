@echo off
title PlantHead Google Drive Authorization
cd /d "%~dp0"

echo ======================================================
echo  PlantHead Google Drive Authorization Tool
echo ======================================================

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo Installing / checking dependencies...
pip install -r requirements.txt

echo.
echo Running authorization script...
python authorize.py

echo.
pause
