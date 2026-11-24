# 管理员版：把网站与隧道注册为真正的 Windows 服务（开机自启，无需登录）
# 用法：开始菜单搜索 PowerShell -> 右键「以管理员身份运行」-> 执行本脚本

#Requires -RunAsAdministrator

$Root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
$Python = (Get-Command python).Source
$Nssm = Join-Path $Root "bin\nssm.exe"

# 若已有用户级计划任务则移除，避免重复启动
Unregister-ScheduledTask -TaskName "HomeServer-AutoStart" -Confirm:$false -ErrorAction SilentlyContinue

function Install-Nssm {
    if (Test-Path $Nssm) { return }
    Write-Host "正在下载 NSSM..."
    $zip = Join-Path $env:TEMP "nssm.zip"
    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $env:TEMP -Force
    Copy-Item (Join-Path $env:TEMP "nssm-2.24\win64\nssm.exe") $Nssm -Force
}

Install-Nssm

# 网站服务
& $Nssm install HomeWeb $Python (Join-Path $Root "server.py") | Out-Null
& $Nssm set HomeWeb AppDirectory $Root | Out-Null
& $Nssm set HomeWeb Start SERVICE_AUTO_START | Out-Null
& $Nssm set HomeWeb AppStdout (Join-Path $Root "logs\web-out.log") | Out-Null
& $Nssm set HomeWeb AppStderr (Join-Path $Root "logs\web-err.log") | Out-Null

# 隧道服务
$Cloudflared = Join-Path $Root "bin\cloudflared.exe"
& $Nssm install HomeTunnel $Cloudflared ("tunnel --config `"$Root\config.yml`" run") | Out-Null
& $Nssm set HomeTunnel AppDirectory $Root | Out-Null
& $Nssm set HomeTunnel Start SERVICE_AUTO_START | Out-Null
& $Nssm set HomeTunnel AppStdout (Join-Path $Root "logs\tunnel-out.log") | Out-Null
& $Nssm set HomeTunnel AppStderr (Join-Path $Root "logs\tunnel-err.log") | Out-Null

Start-Service HomeWeb
Write-Host "服务已安装并启动: HomeWeb, HomeTunnel"
Write-Host "查看状态: Get-Service HomeWeb, HomeTunnel"
