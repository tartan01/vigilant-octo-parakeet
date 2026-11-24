@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [%date% %time%] 启动网站服务... >> logs\startup.log
start "home-web" /min pythonw server.py

timeout /t 2 /nobreak >nul

set /p TOKEN=<token.txt
echo [%date% %time%] 启动 Cloudflare Tunnel... >> logs\startup.log
start "home-tunnel" /min bin\cloudflared.exe tunnel run --token %TOKEN%
