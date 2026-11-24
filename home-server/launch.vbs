' 隐藏启动网站与隧道，随即退出，避免计划任务一直等待
Set ws = CreateObject("WScript.Shell")
root = "C:\Users\romanovsky\WorkBuddy\2026-11-19-16-02-56\home-server"
pythonw = "C:\Users\romanovsky\.workbuddy\binaries\python\versions\3.13.12\pythonw.exe"

' 读取 Token
Set fso = CreateObject("Scripting.FileSystemObject")
Set ts = fso.OpenTextFile(root & "\token.txt", 1)
token = Trim(ts.ReadAll)
ts.Close

ws.CurrentDirectory = root

' 启动网站（pythonw 无窗口）
ws.Run """" & pythonw & """ """ & root & "\server.py""", 0, False

' 启动隧道
ws.Run """" & root & "\bin\cloudflared.exe"" tunnel run --token " & token, 0, False
