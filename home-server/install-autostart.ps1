# 注册「登录时自动启动」计划任务（用户级，无需管理员权限）
# 用法：用 PowerShell 运行此脚本

$TaskName = "HomeServer-AutoStart"
$Root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
$Launcher = Join-Path $Root "launch.ps1"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Launcher`"" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Launch local web server and Cloudflare tunnel" -Force | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "Trigger: at logon"
Write-Host "Test: Start-ScheduledTask -TaskName $TaskName"
