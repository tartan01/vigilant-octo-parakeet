# Start web + tunnel as detached processes via Task Scheduler (survives agent session)
$ErrorActionPreference = "SilentlyContinue"
$TaskName = "HomeServer-StartNow"
$Root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
$Launcher = Join-Path $Root "launch.ps1"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
$Action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Triggered: $TaskName"
