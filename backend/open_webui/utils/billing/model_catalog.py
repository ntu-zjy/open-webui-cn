"""Curated model catalog: the single source of truth for user-visible models.

Edit `MODEL_CATALOG` to add/remove models. The backend routes chat completions
to OpenRouter (set `OPENAI_API_BASE_URLS=https://openrouter.ai/api/v1`), so each
`id` must match an OpenRouter model slug verbatim.

Tier semantics:
  free  -> shown only to free-tier users
  paid  -> shown to plus + pro (and admin)

Free tier models are intentionally OpenRouter's `:free` variants — zero marginal
cost for us. Paid models are the latest top model from each vendor.
"""
from __future__ import annotations

from typing import Optional

MODEL_CATALOG: list[dict] = [
    # ---------- Paid tier — 御三家最新 + 国产三家 ----------
    {
        'id': 'openai/gpt-5.5',
        'name': 'GPT-5.5',
        'vendor': 'openai',
        'tier': 'paid',
        'description': 'OpenAI 最新旗舰',
    },
    {
        'id': 'anthropic/claude-opus-4.7',
        'name': 'Claude Opus 4.7',
        'vendor': 'anthropic',
        'tier': 'paid',
        'description': 'Anthropic 最新旗舰',
    },
    {
        'id': 'google/gemini-3.1-pro-preview',
        'name': 'Gemini 3.1 Pro',
        'vendor': 'google',
        'tier': 'paid',
        'description': 'Google 最新旗舰',
    },
    {
        'id': 'deepseek/deepseek-v4-pro',
        'name': 'DeepSeek V4',
        'vendor': 'deepseek',
        'tier': 'paid',
        'description': '深度求索 V4 Pro',
    },
    {
        'id': 'moonshotai/kimi-k2.6',
        'name': 'Kimi K2.6',
        'vendor': 'moonshot',
        'tier': 'paid',
        'description': '月之暗面 Kimi K2.6',
    },
    {
        'id': 'z-ai/glm-5',
        'name': 'GLM-5',
        'vendor': 'zhipu',
        'tier': 'paid',
        'description': '智谱 GLM-5',
    },
    # ---------- Free tier (OpenRouter free models) ----------
    {
        'id': 'meta-llama/llama-3.3-70b-instruct:free',
        'name': 'Llama 3.3 70B · 免费',
        'vendor': 'meta',
        'tier': 'free',
        'description': 'Meta Llama 3.3 70B Instruct, 免费档可用',
    },
    {
        'id': 'qwen/qwen3-next-80b-a3b-instruct:free',
        'name': 'Qwen3 Next 80B · 免费',
        'vendor': 'qwen',
        'tier': 'free',
        'description': '通义千问 Qwen3 Next 80B, 免费档可用',
    },
    {
        'id': 'z-ai/glm-4.5-air:free',
        'name': 'GLM 4.5 Air · 免费',
        'vendor': 'zhipu',
        'tier': 'free',
        'description': '智谱 GLM 4.5 Air, 免费档可用',
    },
]

# Plan code → tiers visible to that plan
_PLAN_TO_TIERS: dict[str, set[str]] = {
    'free': {'free'},
    'plus': {'free', 'paid'},
    'pro': {'free', 'paid'},
}


def _plan_for(user) -> str:
    if getattr(user, 'role', None) == 'admin':
        return 'pro'
    # Synchronous best-effort: avoid DB lookup on hot path. The quota gate at
    # chat-completion time is authoritative; here we just return a permissive
    # visibility list. Frontend never trusts visibility for access control.
    return 'pro' if getattr(user, 'role', None) in ('admin',) else 'free'


def _stub_model(item: dict) -> dict:
    """Construct a minimal model entry compatible with /api/models response."""
    return {
        'id': item['id'],
        'name': item['name'],
        'object': 'model',
        'created': 0,
        'owned_by': 'openrouter',
        'openai': {'id': item['id']},
        'urlIdx': 0,
        'tags': [],
        'info': {
            'meta': {
                'description': item.get('description', ''),
                'profile_image_url': f'/static/vendors/{item["vendor"]}.svg',
            },
        },
        'connection_type': 'external',
    }


def merge_catalog_into_models(models: list[dict]) -> list[dict]:
    """Ensure every catalog id is present in `models`, adding stubs as needed.

    Called inside `get_all_models` so `app.state.MODELS` contains the curated
    superset — required so chat-completion lookup succeeds for catalog ids that
    the upstream provider hasn't surfaced yet. User-level visibility (free vs
    paid) is still filtered at the /api/models response layer via
    `apply_catalog_filter`.
    """
    have = {m.get('id') for m in models}
    catalog_ids = {item['id'] for item in MODEL_CATALOG}
    # Drop any upstream model not in catalog: developers control the menu.
    out: list[dict] = [m for m in models if m.get('id') in catalog_ids]
    for item in MODEL_CATALOG:
        if item['id'] not in have:
            out.append(_stub_model(item))
    return out


async def apply_catalog_filter(models: list[dict], user) -> list[dict]:
    """Replace `models` with the catalog entries visible to this user.

    Strategy: catalog is the source of truth. Existing entries from upstream
    that match a catalog id are kept (so admin-customised metadata survives),
    and missing entries are synthesized so the frontend always shows the full
    curated set even before OpenRouter is reachable.
    """
    visible_tiers = _PLAN_TO_TIERS.get(_plan_for(user), {'free'})
    catalog_visible = [item for item in MODEL_CATALOG if item['tier'] in visible_tiers]

    by_id = {m.get('id'): m for m in models}
    out: list[dict] = []
    for item in catalog_visible:
        existing = by_id.get(item['id'])
        if existing is not None:
            existing.setdefault('info', {}).setdefault('meta', {}).setdefault(
                'profile_image_url', f'/static/vendors/{item["vendor"]}.svg'
            )
            out.append(existing)
        else:
            out.append(_stub_model(item))
    return out


def vendor_for_model(model_id: Optional[str]) -> Optional[str]:
    if not model_id:
        return None
    for item in MODEL_CATALOG:
        if item['id'] == model_id:
            return item['vendor']
    return None
