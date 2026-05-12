# TODO

按优先级 + 时间窗口分组。✅ 已完成；🚧 进行中；⬜ 待办。

---

## P0 · 部署上线前（卡 MVP 上线）

### 镜像构建
- ✅ `.github/workflows/build.yml` 已写并推送
- 🚧 等待首次 GHCR 构建成功（~15–30 分钟）
- ⬜ 构建成功后把 GHCR package 设为 public（Settings → Change visibility）
- ⬜ 验证 `docker pull ghcr.io/ntu-zjy/open-webui-cn:cn-latest` 在外部能拉到

### Sealos 资源
- ⬜ 开通 Postgres 实例（1C2G / 10GB），记录 `DATABASE_URL`
- ⬜ 开通 Redis 实例（1C512M / 2GB），记录 `REDIS_URL`
- ⬜ 开通 Object Storage Bucket `openwebui-files`，记录 S3 凭据
- ⬜ App Launchpad 部署，env 全量填入
- ⬜ 挂载 PVC `/app/backend/data` 5GB
- ⬜ 开启 Public Access 获取默认域名

### 首次启动
- ⬜ 容器内 `alembic upgrade head`
- ⬜ 容器内 `python -m scripts.seed_plans`
- ⬜ 邮箱注册首个账号（自动 admin）
- ⬜ admin Connections 配置：OpenAI / Anthropic / Gemini / 通义 / 豆包 / DeepSeek / Kimi 七家 API key

### Zpay 接入（账号已开通）
- ⬜ 填 `ZPAY_PID` / `ZPAY_KEY` 到 Sealos env
- ⬜ 填 `ZPAY_NOTIFY_URL` = `https://<sealos-domain>/api/v1/payments/zpay/notify`
- ⬜ 填 `ZPAY_RETURN_URL` = `https://<sealos-domain>/billing/success`
- ⬜ 用最小金额（0.01 元）走一笔支付宝 + 一笔微信，验证：
  - 回调签名通过
  - 订单从 pending → paid
  - 订阅自动延期 31 天
  - 重复回调不重复加时长（幂等）

### 冒烟测试
- ⬜ 邮箱注册 + 聊天
- ⬜ 手机号注册（`SMS_PROVIDER=log`，验证码看 App Logs）+ 聊天
- ⬜ 免费档使用 GPT-4o 返 402
- ⬜ Plus 升级后能用 GPT-4o-mini
- ⬜ `/billing` 用量进度条与实际请求数一致

---

## P1 · MVP 上线后第一周（直接影响用户体验）

### SMS 通道接入
- ⬜ 申请阿里云短信签名（备案文案：AI 助手类目）
- ⬜ 申请验证码模板，记录 `ALIYUN_SMS_TEMPLATE_CODE`
- ⬜ Sealos env 把 `SMS_PROVIDER=log` 改成 `aliyun`，填四个 ALIYUN_* 变量
- ⬜ 验证真实短信能收到、限流生效

### Token 用量精确计费
- ⬜ Hook 进 `backend/open_webui/utils/session_pool.py:118` `stream_wrapper` finally 块
- ⬜ 从最后一个 SSE chunk 的 `usage` 字段提取 token 数
- ⬜ Fallback：tiktoken 估算（OpenAI 流式不返 usage 时）
- ⬜ Anthropic 流式参考 `utils/anthropic.py:405` 已有的累加方式

### 模型下拉过滤
- ⬜ 改 `routers/models.py:120-127`，在返回 items 时按 plan 档位过滤
- ⬜ 免费账号在 UI 模型选择器里不应看到 gpt-4o（目前只是请求时返 402）

### i18n 化新 UI 文案
- ⬜ `/pricing` 和 `/billing` 页面所有写死中文走 `$i18n.t()`
- ⬜ `SmsSignin.svelte` 同上
- ⬜ 在 `src/lib/i18n/locales/zh-CN/translation.json` 加 key

### 静态合规页
- ⬜ `/legal/terms` 用户协议
- ⬜ `/legal/privacy` 隐私政策
- ⬜ 登录页 / 注册按钮下方加链接
- ⬜ 首次注册需勾选同意

---

## P2 · 增长期（用户量起来后再做）

### 计费精细化
- ⬜ 引入"加油包"：Plus 用户买额外 token 包
- ⬜ 引入年付 20% 折扣，写进 `seed_plans.py` 的 `yearly_price_cents`
- ⬜ 模型成本差异定价（GPT-4o vs Haiku 不同倍率）

### 运营后台
- ⬜ Admin 看板：今日/本月新增用户、付费转化、总收入
- ⬜ Admin 手动给账号开通会员（救火用）
- ⬜ 退款流程：admin 触发 Zpay 退款 + 撤销订阅

### 渠道与增长
- ⬜ 微信扫码登录（需要微信开放平台资质，个人难拿，搁置）
- ⬜ 邀请奖励：邀请 1 人，双方各得 7 天 Plus
- ⬜ 站外 SEO 落地页（独立部署）

### 风控
- ⬜ 同 IP 多账号薅羊毛拦截
- ⬜ 异常 API 调用（每秒数十次）熔断
- ⬜ 大模型成本超阈值告警（防 prompt injection 烧 OpenAI 账户）

---

## P3 · 技术债 / 长期

- ⬜ Stripe 兜底通道（海外用户 + Zpay 故障时切换）
- ⬜ 全量 `_memory_store` 改 Redis（captcha.py 在多副本下失效）
- ⬜ 单元测试 + cypress e2e（项目原本有 cypress 框架，加测试用例）
- ⬜ 性能压测：Redis 限流在 100 QPS 时是否准
- ⬜ Postgres 读写分离（用户量 > 1 万考虑）
- ⬜ 接 Sentry 错误收集

---

## 已知 BUG / 待修复

（目前空，发现一个加一行）

---

## 决策记录

| 日期 | 决策 | 原因 |
|---|---|---|
| 2026-05-11 | 用 Zpay 而非 Stripe/微信官方 | 个人无公司，Zpay 是最快接入的合规聚合 |
| 2026-05-11 | 部署 Sealos 新加坡 | 个人无 ICP 备案；新加坡可直连 OpenAI |
| 2026-05-11 | Fork 后定期 rebase | 上游迭代快，长期维护成本可控 |
| 2026-05-11 | 把所有改动塞新文件 | 减少 rebase 冲突面 |
| 2026-05-11 | 手机号自动注册合成 email | User 表 email 字段 NOT NULL，最小侵入做法 |
| 2026-05-11 | 配额闸门放 router 入口而非 middleware | middleware 拦不了流式响应的"中段超额"；router 入口是最简单可靠的拦截点 |
