# Resend 邮件配置指南 — 让 honoweb.com 发送验证码

> 目标：把会员系统的验证码从"页面演示"改为"真实发到用户邮箱"。
> 前提：你有 `honoweb.com`，NS 已在 Cloudflare；后端已预留 `send_code()` 接口，改这一处即可。

---

## 为什么必须用 Resend 这类服务

自己在本机搭 SMTP 服务器发全球邮件，2026 年行不通：

- 运营商封禁家宽/手机网络的 25、465、587 出站端口
- 自建 IP 没有发信信誉，邮件直接进垃圾箱或被拒收

Resend 是面向开发者的邮件 API，免费额度 **每月 3000 封 / 每天 100 封 / 1 个域名**，你的验证码场景完全够用。用你自己的域名发信，收件人看到的是 `noreply@honoweb.com`，不会有"via resend.com"字样。

---

## 第一步：注册 Resend 并添加域名

1. 打开 https://resend.com 注册（免费，无需信用卡）
2. 进入 **Domains** → **Add Domain**
3. 输入 `honoweb.com`，区域默认 US East 即可
4. Resend 会生成 3–4 条 DNS 记录，**先别关页面**，下一步要用

## 第二步：在 Cloudflare 添加 DNS 记录

进入 Cloudflare → 你的域名 → **DNS → Records**，把 Resend 给的记录逐条添加：

| 类型 | 名称 | 内容 | 作用 |
|---|---|---|---|
| TXT | `@` | `v=spf1 include:amazonses.com ~all`（以 Resend 给出的为准） | SPF：授权 Resend 发信 |
| CNAME | `resend._domainkey` | Resend 给的一串地址 | DKIM：邮件签名验证 |
| CNAME | `<随机>._domainkey` | Resend 给的（如有） | DKIM 第二条 |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@honoweb.com` | DMARC：验证策略 |

**三个关键点**：

1. **DKIM 值对空格敏感**，从 Resend 页面原样复制，不要手动改
2. **所有邮件相关记录必须设为 "DNS only"（灰云）**，不能开 Cloudflare 代理（橙云）——邮件 DNS 走代理会失效
3. **不要动 MX 记录**：如果你用 Cloudflare Email Routing 收信，MX 保留；发信用 SPF/DKIM/DMARC，两者不冲突
4. 如果你已有 SPF 记录（比如 Google Workspace 的），**合并到一条**，不要建两条 SPF

添加完回 Resend 点 **Verify**，通常几分钟内变绿，最长可能 24 小时。

## 第三步：创建 API Key

1. Resend → **API Keys** → **Create API Key**
2. 名称随意（如 `honoweb-membersite`）
3. 权限选 **Sending access**，可限定域名
4. 复制 Key（`re_xxx...`）——**只显示一次**，妥善保存

## 第四步：生成发信邮箱

域名验证后，Resend 允许用该域名下任意地址发信，例如：

```
noreply@honoweb.com
藤蔓会 <hello@honoweb.com>
```

无需在 Resend 单独创建邮箱，DNS 验证通过后即可用。

---

## 第五步：改代码（只需改一个函数）

打开 `server.py`，找到 `send_code()` 函数。当前是演示版：

```python
def send_code(email, code):
    print(f"[MAIL-DEMO] to={email} code={code}", flush=True)
    return True
```

### 方案 A：用 REST API（推荐，零依赖，符合当前零第三方库原则）

先在 PowerShell 设置环境变量（临时，当前会话有效）：

```powershell
$env:RESEND_API_KEY = "re_你的key"
```

永久设置（用户级，重启后仍在）：

```powershell
[Environment]::SetEnvironmentVariable("RESEND_API_KEY","re_你的key","User")
```

然后把 `send_code()` 替换为：

```python
import urllib.request

def send_code(email, code):
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print("[MAIL] RESEND_API_KEY not set", flush=True)
        return False
    payload = json.dumps({
        "from": "藤蔓会 <noreply@honoweb.com>",
        "to": [email],
        "subject": "您的入会验证码",
        "html": f"""
        <div style="font-family:Georgia,serif;color:#2d5016;background:#f5f0e1;padding:32px;border-radius:24px">
          <h2 style="margin:0 0 12px">藤蔓会 · 入会信笺</h2>
          <p>您的验证码是：</p>
          <div style="font-size:32px;letter-spacing:8px;color:#8b6db5;margin:18px 0">{code}</div>
          <p style="font-size:13px;color:#4a7c3f">验证码 5 分钟内有效。若非本人操作，请忽略此邮件。</p>
        </div>"""
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[MAIL] sent to {email}: {resp.status}", flush=True)
            return True
    except Exception as e:
        print(f"[MAIL] failed: {e}", flush=True)
        return False
```

### 方案 B：用官方 SDK（功能全，但要装包）

```bash
pip install resend
```

```python
import resend
resend.api_key = os.environ.get("RESEND_API_KEY", "")

def send_code(email, code):
    r = resend.Emails.send({
        "from": "藤蔓会 <noreply@honoweb.com>",
        "to": [email],
        "subject": "您的入会验证码",
        "html": f"<p>验证码：<b style='font-size:28px'>{code}</b>，5 分钟内有效。</p>",
    })
    return "id" in r
```

**建议用方案 A**——你现在零第三方依赖，标准库方案最省事。

## 第六步：关闭演示验证码

改完 `send_code()` 后，把 `do_POST` 里 `/api/send-code` 的响应中的 `demoCode` 字段删掉：

```python
return self._json({"ok": True, "demoCode": code, "ttl": CODE_TTL})
```
改为：
```python
return self._json({"ok": True, "ttl": CODE_TTL})
```

前端 `index.html` 里把演示验证码框隐藏即可（找到 `demo-code` 那个 div，加 `style="display:none"`；或等下一步我帮你清理）。

## 第七步：测试

1. 重启会员系统服务（先停掉 pythonw 再运行 `server.py`）
2. 在页面输入你自己的邮箱，点"寄出验证码"
3. 查收邮件（垃圾箱也看看），填入验证码
4. 到 Resend 后台 **Logs** 能看到发送记录

---

## 常见坑

| 现象 | 原因 | 解决 |
|---|---|---|
| Resend 域名一直不验证 | DNS 记录开了橙云代理 | 改成 DNS only 灰云 |
| 邮件进垃圾箱 | SPF/DKIM/DMARC 没配全或没生效 | 等 DNS 传播，检查记录 |
| 401 Unauthorized | From 地址域名和验证的域名不一致 | 必须用 `xxx@honoweb.com` |
| 提示已有 SPF 记录 | 一条域名只能有一条 SPF | 合并值到现有 TXT 记录 |
| 发信成功但收不到 | 免费额度用完 / 收件箱拦截 | 看 Resend Logs 和垃圾箱 |

## 关于"用本机域名发全球邮件"

严格说，邮件不是"从本机发出"的——本机调用 Resend 的 API，由 Resend 的服务器发出。但**发件人显示的是 `@honoweb.com`**，对你的用户来说完全等价，而且送达率远高于自建。这是目前唯一现实可行的做法。

---

## 需要你做的

1. 注册 Resend，添加 `honoweb.com`，把 DNS 记录发我确认（或你自己加）
2. 创建 API Key，**不要发给我**——你自己在本机设置环境变量即可
3. 域名验证通过后告诉我，我帮你改代码、关演示模式、重启测试
