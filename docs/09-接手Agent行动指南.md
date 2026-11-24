# 09 — 接手 Agent 行动指南

> 这份文档回答："我接手后，遇到具体任务该怎么做？"

## 第一步：判断当前状态（每次接手先做）

```bash
# 1. 公网是否通
curl -sSL -o /dev/null -w "%{http_code}\n" https://www.honoweb.com/

# 2. 本机进程
tasklist | grep -iE 'cloudflared|pythonw'

# 3. 项目文件是否齐全
ls "<home-server>"
```

判断：
- 公网 200 + 一个 pythonw + 一个 cloudflared → 一切正常，无需干预
- 公网 200 但两个 pythonw → 有重复进程，见文档 07
- 公网不通 → 按文档 07 的排错流程逐层检查
- 文件缺失 → 按文档 02/03/05 重建

## 常见任务的执行步骤

### 任务 A：确认开机自启是否生效

1. 读 `logs\setup-log.txt`，看是否有 `SUCCESS: HomeServer-BootStart registered`
2. 让用户双击 `验证开机任务.bat`（UAC 点"是"），看 LastTaskResult 是否为 0
3. 终极验证：重启电脑不登录，手机访问域名

注意：不要用普通权限会话查 SYSTEM 任务，会误判为不存在。

### 任务 B：新增一个网站/服务

1. 在本机写好服务，监听一个未占用端口（如 3000）
2. Cloudflare 网页加一条 Public Hostname：`子域名.honoweb.com → HTTP → 127.0.0.1:3000`（见文档 04）
3. 若要开机自启：把启动命令加进 `launch.ps1`（注意防重复逻辑）
4. 验证：`curl https://子域名.honoweb.com/`

进阶（推荐）：先按文档 08 引入 Caddy，之后加服务只改本机配置，不用碰 Cloudflare。

### 任务 C：重启/修复服务

```bash
# 停止全部
（用 PowerShell）Get-Process cloudflared,pythonw | Stop-Process -Force
# 重新启动（用户级，无需提权）
（用 PowerShell）& "<home-server>\launch.ps1"
# 验证
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/
```

### 任务 D：把整套东西迁到新机器

1. 复制整个 `home-server` 目录到新机器
2. 修改所有脚本里的绝对路径（`$Root`、`$Python`）
3. 新机器安装 Python 和 cloudflared（见文档 02，注意用镜像下载）
4. 在新账号 Cloudflare 重新创建隧道，获取新 Token，替换 `token.txt`
5. 重新配 Public Hostname（文档 04）
6. 重新运行 `一键配置开机自启.bat`（文档 06）

### 任务 E：查看访问量，决定是否迁移正式服务器

```bash
wc -l < logs/visits.jsonl
# 或公网 curl /api/stats
```
按日统计：每条记录有 time 字段，可用 Python 聚合。用户计划访问量大后迁正式服务器。

## 权限与安全红线

1. **Token 不外泄**：不要复制明文到新文档/聊天/仓库
2. **提权靠用户**：需要管理员操作时，准备脚本让用户本机双击，Agent 不代执行（安全策略禁止）
3. **bat 纯 ASCII**：新增 bat 脚本一律英文，避免乱码
4. **不要真的重启用户电脑**（除非明确要求）：会中断会话；用模拟验证代替

## 已知限制（坦诚告知用户）

- 免费 Cloudflare Tunnel 在国内延迟 100–300ms，晚高峰波动，不适合大文件/视频
- 服务条款不适合大流量分发，量大后应迁正式服务器
- 手机热点/家宽连入站端口被封不影响本方案（隧道走出站），但运营商合约可能禁止对外经营服务
- 未备案域名走境外节点，国内访问速度无保证；正式对外经营需 ICP 备案

## 上下文来源

本套文档由 2026-11-19 至 2026-11-21 的完整任务对话压缩整理，涵盖：方案调研、环境搭建、网站开发、Cloudflare 配置、隧道接入、开机自启调试、验证排错、扩展规划。所有数值（隧道 ID、文件大小、验证结果）均来自实际执行记录。
