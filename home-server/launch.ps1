$ErrorActionPreference = "SilentlyContinue"
$Root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
$Python = "C:\Users\romanovsky\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"
$Site = Join-Path $Root "membersite\server.py"
$Cf = Join-Path $Root "bin\cloudflared.exe"
$Token = (Get-Content (Join-Path $Root "token.txt") -Raw).Trim()
$Log = Join-Path $Root "logs\launch.log"

function Write-Log($msg) {
    Add-Content -Path $Log -Value ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg)
}

# Deduplication: detect existing processes and skip if already running
$portBusy = $false
$probe = New-Object System.Net.Sockets.TcpClient
try { $probe.Connect('127.0.0.1', 8080); $portBusy = $probe.Connected } catch {} finally { $probe.Close() }
$tunnelRunning = Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" | Where-Object { $_.CommandLine -like "*$Root\bin\cloudflared.exe*" }

if (-not $portBusy) {
    Start-Process -FilePath $Python -ArgumentList "`"$Site`"" -WorkingDirectory (Split-Path $Site) -WindowStyle Hidden
    Write-Log "Started membersite on 8080"
} else {
    Write-Log "Web server already listening on 8080 - skipped"
}

if (-not $tunnelRunning) {
    Start-Process -FilePath $Cf -ArgumentList "tunnel", "run", "--token", $Token -WorkingDirectory $Root -WindowStyle Hidden
    Write-Log "Started cloudflared tunnel"
} else {
    Write-Log "Tunnel already running (PID $($tunnelRunning.ProcessId -join ','))"
}
