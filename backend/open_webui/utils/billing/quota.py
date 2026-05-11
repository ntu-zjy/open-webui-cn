"""Quota / model-tier gate for chat completion requests.

`check_quota` is called at the entrypoint of OpenAI / Ollama / other chat
routes. On insufficient subscription or exhausted monthly allowance it
raises HTTPException(402) which propagates to the client.

Plan resolution:
  - the user's active subscription -> plan_code
  - if none, fall back to the free plan (created by seed_plans.py)

Model whitelist:
  - plans.allowed_model_pattern is a JSON-encoded list of glob-like patterns
    (`*` as wildcard); a model matching ANY pattern is permitted.
  - additionally, MODEL_TIER_MAP env var (JSON: {plan_code: [patterns,...]}) is
    merged on top so ops can hot-swap without DB migrations.

Usage quota:
  - plans.monthly_msg_limit and monthly_token_limit cap usage. -1 = unlimited.
  - the month-window sum is taken from usage_log.
"""
import fnmatch
import json
import logging
import os
import time
from typing import Optional

from fastapi import HTTPException, status

from open_webui.models.plans import FREE_PLAN_CODE, PlanModel, Plans
from open_webui.models.subscriptions import Subscriptions
from open_webui.models.usage_logs import UsageLogs

log = logging.getLogger(__name__)


_cached_tier_map: Optional[dict[str, list[str]]] = None


def _load_tier_map_from_env() -> dict[str, list[str]]:
    global _cached_tier_map
    if _cached_tier_map is not None:
        return _cached_tier_map
    raw = os.environ.get('MODEL_TIER_MAP', '').strip()
    if not raw:
        _cached_tier_map = {}
        return _cached_tier_map
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError('MODEL_TIER_MAP must be a JSON object')
        _cached_tier_map = {str(k): [str(p) for p in v] for k, v in parsed.items() if isinstance(v, list)}
    except Exception as e:
        log.error(f'Invalid MODEL_TIER_MAP JSON, ignoring: {e}')
        _cached_tier_map = {}
    return _cached_tier_map


def _patterns_for_plan(plan: PlanModel) -> list[str]:
    patterns: list[str] = []
    if plan.allowed_model_pattern:
        try:
            decoded = json.loads(plan.allowed_model_pattern)
            if isinstance(decoded, list):
                patterns.extend(str(p) for p in decoded)
            elif isinstance(decoded, str):
                patterns.append(decoded)
        except Exception:
            patterns.extend(p.strip() for p in plan.allowed_model_pattern.split(',') if p.strip())
    env_map = _load_tier_map_from_env()
    if plan.code in env_map:
        patterns.extend(env_map[plan.code])
    # A plan with no patterns at all permits everything (fail-open for admins).
    return patterns


def _model_allowed(model: str, plan: PlanModel) -> bool:
    if not model:
        return True
    patterns = _patterns_for_plan(plan)
    if not patterns:
        return True
    return any(fnmatch.fnmatchcase(model, pat) for pat in patterns)


async def get_plan_for_user(user_id: str, role: Optional[str] = None, db=None) -> Optional[PlanModel]:
    if role == 'admin':
        # Admins are not gated.
        return None
    sub = await Subscriptions.get_active_for_user(user_id, db=db)
    plan_code = sub.plan_code if sub else FREE_PLAN_CODE
    return await Plans.get_by_code(plan_code, db=db)


async def check_quota(user, model: str, *, db=None) -> None:
    """Raise HTTPException(402) if user can't run this request."""
    if user is None:
        return  # let upstream auth layer handle anonymous

    plan = await get_plan_for_user(user.id, role=getattr(user, 'role', None), db=db)
    if plan is None:
        return  # admin or no free plan seeded -> pass through

    if not _model_allowed(model, plan):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                'error': 'model_not_in_plan',
                'message': f'当前订阅档位（{plan.name}）不包含模型 {model}，请升级套餐',
                'plan_code': plan.code,
                'upgrade_url': '/pricing',
            },
        )

    if plan.monthly_msg_limit == 0 or plan.monthly_token_limit == 0:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                'error': 'plan_disabled',
                'message': '当前档位不允许使用，请升级套餐',
                'plan_code': plan.code,
                'upgrade_url': '/pricing',
            },
        )

    if plan.monthly_msg_limit < 0 and plan.monthly_token_limit < 0:
        return  # unlimited

    summary = await UsageLogs.month_summary(user.id, db=db)

    if 0 <= plan.monthly_msg_limit <= summary['messages']:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                'error': 'msg_limit_reached',
                'message': f'本月消息数 ({summary["messages"]}) 已达上限 ({plan.monthly_msg_limit})，请升级套餐',
                'plan_code': plan.code,
                'upgrade_url': '/pricing',
            },
        )

    if 0 <= plan.monthly_token_limit <= summary['total_tokens']:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                'error': 'token_limit_reached',
                'message': f'本月 token 用量 ({summary["total_tokens"]}) 已达上限 ({plan.monthly_token_limit})，请升级套餐',
                'plan_code': plan.code,
                'upgrade_url': '/pricing',
            },
        )


def invalidate_tier_map_cache() -> None:
    """Call this after MODEL_TIER_MAP env changes at runtime."""
    global _cached_tier_map
    _cached_tier_map = None
