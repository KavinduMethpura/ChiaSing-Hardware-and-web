@echo off
title Copy Google Drive Token to Raspberry Pi
cd /d "%~dp0"

echo ======================================================
echo  Copy Google Drive Token to PlantHead Pi
echo ======================================================

if not exist "gdrive_token.json" (
    echo [ERROR] 'gdrive_token.json' not found!
    echo Please run 'run_auth.bat' first to generate the token.
    pause
    exit /b 1
)

set /p PI_HOST="Enter Pi hostname or IP (default: planthead1.local): "
if "%PI_HOST%"=="" set PI_HOST=planthead1.local

set /p PI_USER="Enter Pi username (default: planthead1): "
if "%PI_USER%"=="" set PI_USER=planthead1

echo.
echo Copying gdrive_token.json to %PI_USER%@%PI_HOST%:~/planthead/secrets/ ...
scp gdrive_token.json %PI_USER%@%PI_HOST%:~/planthead/secrets/

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Token copied successfully to %PI_HOST%!
) else (
    echo.
    echo [ERROR] scp failed. Make sure the Pi is online and SSH is enabled.
)

echo.
pause
