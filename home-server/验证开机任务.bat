@echo off
cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting admin, please click YES...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
    exit /b
)

echo === Boot task verification ===
echo Task info:
powershell -NoProfile -Command "Get-ScheduledTask -TaskName 'HomeServer-BootStart' | Select-Object TaskName,State,@{N='User';E={$_.Principal.UserId}},@{N='Trigger';E={$_.Triggers[0].CimClass.CimClassName}} | Format-List"
echo.
echo Launching task now (simulating boot)...
powershell -NoProfile -Command "Start-ScheduledTask -TaskName 'HomeServer-BootStart'; Start-Sleep -Seconds 8; Get-ScheduledTaskInfo -TaskName 'HomeServer-BootStart' | Select-Object LastRunTime,LastTaskResult | Format-List"
echo.
echo Processes:
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe' OR Name='pythonw.exe'\" | Select-Object ProcessId,Name | Format-Table -AutoSize"
echo.
echo See the result above. Press any key to close.
pause
