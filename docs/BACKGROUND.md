# 项目背景

## 项目定位

本仓 (`ntu-zjy/open-webui-cn`) 是 [open-webui/open-webui](https://github.com/open-webui/open-webui) 的中国大陆商业化 fork，定位为面向大陆个人用户的付费 AI 聊天 SaaS。基于上游 `v0.9.5` 起步，长期分支 `feat/cn-payment`。

## 目标用户

- **主要**：中国大陆用户，付费意愿来自 ChatGPT 大陆访问受限 + 国产模型集成
- **次要**：海外华人（共用同一站点，国际信用卡走 Stripe 兜底——目前未实装）

## 运营约束

| 维度 | 现状 | 影响 |
|---|---|---|
| 主体 | 个人，无公司 | 不能直接对接微信/支付宝官方商户号；走 Zpay 聚合 |
| 域名 | 无大陆备案 | 部署在 Sealos 新加坡区，使用 Sealos 默认域名 |
| 合规 | 无生成式 AI 备案 | 法律风险存在但 MVP 阶段可控；低调运营 |
| 模型 | 不自托管 | 全部代理上游 API；服务器在新加坡可直连 OpenAI/Anthropic |

## 商业模型

**订阅制**，目前 3 档：

- **免费**：每月 50 条消息 / 20 万 token，仅国产模型（Qwen、DeepSeek）
- **Plus**：¥29/月，每月 1500 条 / 500 万 token，开通主流海外模型 mini 系列
- **Pro**：¥99/月，无限额度，全部模型含推理模型（o1、Opus）

详细价格点和 token 上限可后续在 admin 后台或 `scripts/seed_plans.py` 调整。

## 关键依赖

| 依赖 | 用途 | 状态 |
|---|---|---|
| Open WebUI 主仓 | 上游代码，每周一版 | 长期 rebase 进新版本 |
| Sealos 新加坡 | 容器宿主 + Postgres + Redis + S3 | 已开户 |
| Zpay (z-pay.cn) | 个人聚合支付（支付宝/微信） | 已开户，待填 `ZPAY_PID/KEY` |
| 阿里云短信 | 手机号验证码 | 暂缓申请；用 `SMS_PROVIDER=log` 把验证码打日志 |
| GHCR | 容器镜像仓库 | 通过 GitHub Actions 自动推 |
| OpenAI/Anthropic/Gemini | 海外模型 | 由运营在 admin Connections 配 key |
| 通义/豆包/DeepSeek/Kimi | 国产模型（OpenAI 兼容端点） | 同上 |

## 风险清单

1. **Zpay 通道**：第三方聚合非官方支付，存在突然封号/押款风险。建议：余额及时提现 + 后期备 Stripe 兜底
2. **生成式 AI 合规**：境外主体面向大陆收费理论上需备案，个人无法备案——MVP 阶段低调运营，不可消除
3. **短信轰炸**：上线后开启阿里云短信前，必须保留图形验证码 + 多维限流（已实装）
4. **Rebase 冲突**：上游主仓发版频繁。修改尽量塞新文件，原文件只挂"接口点"（已落实）
5. **Token 计量准确度**：OpenAI 流式响应末尾 `usage` 字段并非所有模型/版本都返回，目前仅按消息数计费稳定；token 计费需要后续加 `stream_wrapper` hook

## 维护策略

- `feat/cn-payment` 为商业化主分支，所有功能在此演进
- 每 1–2 周从 `upstream/main` rebase 一次，把上游 bug 修复和新功能拉过来
- 改动尽量在新文件，原文件只动 import 行和单行 hook，最小化 rebase 冲突
- 关键节点打 tag：`cn-v0.x.y`，对应 GHCR `cn-vX.Y.Z`
