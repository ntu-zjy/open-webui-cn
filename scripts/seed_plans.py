"""Seed the three default subscription plans (free / plus / pro).

Run after `alembic upgrade head`:
    python -m scripts.seed_plans

Re-running is safe — plans are upserted by code.
"""
import asyncio
import json
import sys

# Allow running from repo root: `python -m scripts.seed_plans`
sys.path.insert(0, 'backend')

from open_webui.models.plans import Plans  # noqa: E402


PLANS = [
    {
        'code': 'free',
        'name': '免费版',
        'description': '体验国产模型，每月有限额度',
        'monthly_price_cents': 0,
        'yearly_price_cents': None,
        'monthly_msg_limit': 50,
        'monthly_token_limit': 200_000,
        'allowed_model_pattern': json.dumps(['qwen-turbo*', 'deepseek-chat*']),
        'features_json': {'model_count': 2, 'support': '社区'},
        'display_order': 10,
    },
    {
        'code': 'plus',
        'name': 'Plus 月付',
        'description': '解锁主流海外模型 + 高额度',
        'monthly_price_cents': 19900,
        'yearly_price_cents': 199000,
        'monthly_msg_limit': 1500,
        'monthly_token_limit': 5_000_000,
        'allowed_model_pattern': json.dumps([
            'qwen-*', 'deepseek-*', 'kimi*', 'doubao-*',
            'gpt-4o-mini*', 'claude-haiku*', 'gemini-flash*'
        ]),
        'features_json': {'support': '邮件支持', 'priority': False},
        'display_order': 20,
    },
    {
        'code': 'pro',
        'name': 'Pro 月付',
        'description': '解锁全部模型 + 高优先级 + 推理模型',
        'monthly_price_cents': 39900,
        'yearly_price_cents': 399000,
        'monthly_msg_limit': -1,
        'monthly_token_limit': -1,
        'allowed_model_pattern': json.dumps(['*']),
        'features_json': {'support': '7×24', 'priority': True, 'reasoning_models': True},
        'display_order': 30,
    },
]


async def main() -> None:
    for plan in PLANS:
        result = await Plans.upsert(plan)
        print(f'  upserted: {result.code} ({result.name}) ¥{result.monthly_price_cents/100:.2f}/月')


if __name__ == '__main__':
    asyncio.run(main())
