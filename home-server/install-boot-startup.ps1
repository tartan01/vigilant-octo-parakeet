$ErrorActionPreference = "Stop"
$Root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
$Log = Join-Path $Root "logs\setup-log.txt"
$TaskName = "HomeServer-BootStart"
$Launcher = Join-Path $Root "launch.ps1"

function L($m) { Add-Content -Path $Log -Value ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

L "=== START ==="
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
L "User: $($id.Name)  IsAdmin: $isAdmin"

if (-not $isAdmin) {
    L "ERROR: not administrator. Aborting."
    Write-Host "ERROR: not administrator"
    exit 1
}

try {
    Unregister-ScheduledTask -TaskName "HomeServer-AutoStart" -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    L "Old tasks removed"

    $Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Launcher`"" -WorkingDirectory $Root
    $Trigger = New-ScheduledTaskTrigger -AtStartup
    $Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    L "Components created"

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Boot launch of web server and tunnel" -Force | Out-Null
    L "SUCCESS: $TaskName registered"

    $verify = Get-ScheduledTask -TaskName $TaskName
    L "Verify: state=$($verify.State) user=$($verify.Principal.UserId) trigger=$($verify.Triggers[0].CimClass.CimClassName)"
    Write-Host "SUCCESS"
} catch {
    L "ERROR: $($_.Exception.Message)"
    Write-Host "ERROR: $($_.Exception.Message)"
}
L "=== END ==="
