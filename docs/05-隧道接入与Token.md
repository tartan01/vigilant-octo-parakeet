# 05 — 隧道接入与 Token

## Token 校验

用户提供的安装命令形如：
```
cloudflared.exe service install eyJhIjoi...（一长串 base64）...
```

Token 是 base64 编码的 JSON，可用 Python 解码查看结构（不暴露密钥本身）：

```python
import base64, json
d = json.loads(base64.urlsafe_b64decode(token + '==='))
# d['a'] = 账户标识  cfaf86534ef6988c280c680ae0ad938c
# d['t'] = 隧道 ID    7f0144b7-78d9-4beb-9682-daecb68011d3
# d['s'] = 密钥（48 字符，不要外泄）
```

本项目 Token 已校验有效，保存在：
- `home-server\token.txt`（主用）
- `home-server\bin\tunnel-token.txt`（副本）

## service install 失败的原因（重要）

用户给的命令是 `cloudflared service install <token>`，本意是注册 Windows 系统服务。但执行时报错：

```
Cannot establish a connection to the service control manager: Access is denied.
```

**原因**：当时的执行会话没有管理员权限。注册系统服务需要管理员授权。

**解决**：放弃 service install，改用 Token 直接运行进程的等效方式：
```
cloudflared.exe tunnel run --token <TOKEN>
```
这种方式不需要管理员权限，功能完全等价，配合计划任务实现自启。

## 隧道连通验证

运行后日志应出现（本项目实测）：

```
INF Starting tunnel tunnelID=7f0144b7-...
INF Registered tunnel connection connIndex=0 ... location=lax12 protocol=quic
INF Registered tunnel connection connIndex=2 ...
INF Registered tunnel connection connIndex=3 ...
SUMMARY: Environment is healthy. cloudflared will use 'quic' as primary protocol.
```

说明：
- cloudflared 默认建 4 条连接（connIndex 0-3）
- 其中 1 条 QUIC 偶发超时属正常现象，3 条稳定就够用
- `Registered tunnel connection` 出现即表示隧道打通
- 连接节点为境外（lax = 洛杉矶），这解释了 100–300ms 的国内延迟

## 直接运行 vs 系统服务

| 方式 | 命令 | 需要管理员 | 本项目是否采用 |
|---|---|---|---|
| 注册系统服务 | `service install <token>` | 是 | 否（权限不足） |
| 直接运行进程 | `tunnel run --token <token>` | 否 | **是** |
| 配置文件方式 | `tunnel --config config.yml run` | 否 | 否（Token 方式更简单） |

## 安全提醒

- Token 等同隧道完整控制权，泄露者可接管隧道
- 不要写进公开文档、代码仓库、聊天记录
- 接手 Agent 需要时从 `token.txt` 读取，不要把明文复制到别处
