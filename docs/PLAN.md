# 当前计划

## 架构总览

```
┌────────────────── Sealos 新加坡 ──────────────────┐
│                                                   │
│  Caddy Ingress (默认域名 + 自动 TLS)               │
│         │                                         │
│         ▼                                         │
│  open-webui (FastAPI + SvelteKit)                 │
│   ├─ routers/auths.py        (邮箱/密码、签名一次微调)│
│   ├─ routers/auths_sms.py    [新] 手机号+短信        │
│   ├─ routers/billing.py      [新] 订阅查询/用量      │
│   ├─ routers/payments.py     [新] Zpay 下单/回调     │
│   ├─ routers/openai.py       (单行 check_quota hook) │
│   ├─ routers/ollama.py       (同上)                 │
│   ├─ utils/sms/aliyun.py     [新] 阿里云 SMS         │
│   ├─ utils/captcha.py        [新] Pillow 图形验证码 │
│   ├─ utils/billing/quota.py  [新] 配额闸门           │
│   ├─ utils/billing/usage.py  [新] token 计量         │
│   └─ utils/billing/zpay.py   [新] Zpay 签名/验签     │
│         │                                         │
│         ├──► Postgres (Sealos 托管)               │
│         ├──► Redis    (验证码 + 限流 + 用量缓存)    │
│         └──► S3       (Sealos Object Storage)     │
│                                                   │
└───────────────────────────────────────────────────┘
                  │                  │
                  ▼                  ▼
        OpenAI / Anthropic /  通义 / 豆包 / DeepSeek /
        Gemini 官方 API        Kimi (OpenAI 兼容端点)
```

## 已实现功能（v0.1）

### 后端
- ✅ 手机号 + 短信验证码登录（图形验证码 + 60s 限流 + 5 次/小时 IP 限流）
- ✅ 手机号自动注册（合成邮箱 + 随机密码，避免冲突）
- ✅ 邮箱+密码、手机号+密码、LDAP 三条原生路径并存
- ✅ 订阅模型：`plan` / `subscription` / `usage_log` 表
- ✅ 配额闸门：`check_quota(user, model)` 在 chat completion 入口拦截，超额返 402
- ✅ 模型分级：plan.allowed_model_pattern + `MODEL_TIER_MAP` env 双层
- ✅ Zpay 支付：订单生成、签名跳转、异步回调验签、幂等续期订阅
- ✅ 订单状态机：pending → paid / expired / refunded
- ✅ Token 用量记录（仅非流式响应；流式 hook TODO）

### 前端
- ✅ 登录页 Tab 切换（手机号/邮箱/LDAP），默认手机号
- ✅ `/pricing` 套餐对比 + Zpay 跳转
- ✅ `/billing` 订阅状态 + 用量进度条 + 订单历史
- ✅ `/billing/success` 支付回跳轮询
- ✅ UserMenu 加 "订阅与账单" / "升级套餐" 入口

### 运维
- ✅ `deploy/sealos/env.example` 全量环境变量清单
- ✅ `scripts/seed_plans.py` 初始化三档套餐
- ✅ `.github/workflows/build.yml` GHCR 自动构建
- ✅ `GRAVATAR_BASE_URL` env + Cravatar 镜像支持
- ✅ Dependabot/上游冗余 workflow 已禁用

## 数据库

3 个新 Alembic 迁移，按顺序：

1. `a1b2c3d4e5f6_add_phone_and_verification_code.py` — `user.phone` 列 + `verification_code` 表
2. `b2c3d4e5f6a7_add_billing_tables.py` — `plan` / `subscription` / `usage_log`
3. `c3d4e5f6a7b8_add_orders_table.py` — `order`

链在上游最新 head `f1e2d3c4b5a6_add_access_grant_table` 之后。

## 当前进度（截至本次会话）

| 阶段 | 状态 |
|---|---|
| ① 中文化 + Sealos 部署 | ✅ 代码完成，待 Sealos 部署 |
| ② 手机号 + SMS 认证 | ✅ 代码完成（SMS 通道用 stub） |
| ③ 订阅与配额 | ✅ 后端完成，前端基础页面完成 |
| ④ Zpay 支付 | ✅ 后端完成，前端跳转完成 |
| ⑤ 多源模型代理与分级 | ✅ env-driven，运维 admin Connections 配 key |
| ⑥ 收尾 | ✅ Cravatar、env 清单完成；用户协议/隐私政策待写 |

总代码量：37 个文件 / 约 2820 行新增

## 关键复用点（不要重复造轮子）

| 已有功能 | 路径 |
|---|---|
| Rate limiter | `backend/open_webui/utils/rate_limit.py` |
| Redis client | `backend/open_webui/utils/redis.py:166` |
| JWT 签发 | `backend/open_webui/routers/auths.py:119` `create_session_response` |
| 用户创建 | `backend/open_webui/routers/auths.py:683` `signup_handler` |
| 用户依赖注入 | `backend/open_webui/utils/auth.py:458` `get_verified_user` |
| Usage 字段标准化 | `backend/open_webui/utils/response.py:11` `normalize_usage` |
| 后端配置 + 持久化 | `backend/open_webui/config.py` `PersistentConfig` |

## 部署流程

1. GitHub push → Actions 自动构建 → 推到 `ghcr.io/ntu-zjy/open-webui-cn:cn-latest`
2. Sealos 开通 Postgres / Redis / Object Storage，复制连接串
3. Sealos App Launchpad 部署，env 用 `deploy/sealos/env.example` 填充
4. 容器内跑：`alembic upgrade head` + `python -m scripts.seed_plans`
5. 邮箱注册第一个账号 → 自动 admin → 配置上游 API key（admin Connections）

详细步骤见会话记录或下次直接看 `deploy/sealos/env.example` 的注释。

## 下次 rebase 上游主仓时

```bash
git fetch upstream
git rebase upstream/main
# 预期冲突点（很少）：
#   - backend/open_webui/main.py（router 挂载段）
#   - backend/open_webui/routers/auths.py（signup_handler 改 password Optional）
#   - backend/open_webui/routers/openai.py（一行 check_quota）
#   - backend/open_webui/routers/ollama.py（一行 check_quota）
#   - backend/open_webui/models/users.py（phone 字段）
#   - backend/open_webui/utils/misc.py（GRAVATAR_BASE_URL）
#   - src/routes/auth/+page.svelte（Tab 切换）
#   - src/lib/components/layout/Sidebar/UserMenu.svelte（菜单项）
#   - src/lib/utils/safeImageUrl.ts（cravatar 白名单）
# 所有 .py 新文件、新迁移、新 Svelte 文件均无冲突
```
