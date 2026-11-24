@echo off
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges, please click YES on UAC...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
    exit /b
)

echo Administrator OK. Configuring...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-boot-startup.ps1"
echo.
echo See logs\setup-log.txt for details.
pause
