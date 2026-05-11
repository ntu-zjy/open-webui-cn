"""Record token usage from chat-completion responses.

The OpenAI Python SDK and OpenAI-compatible servers return a `usage` field
in the response body (non-streaming) or in the very last SSE chunk before
`[DONE]` (streaming with stream_options.include_usage=true).

For non-stream responses, call `record_from_response_dict(user_id, model, body)`.
For stream responses, accumulate the last-chunk usage in the existing
`stream_wrapper` and call the same recorder at finalization. Anthropic stream
parsing already accumulates usage in `utils/anthropic.py:~405`; reuse the
shape returned there.
"""
import logging
from typing import Optional

from open_webui.models.usage_logs import UsageLogs

log = logging.getLogger(__name__)


def _extract_usage(payload: dict) -> Optional[dict]:
    if not isinstance(payload, dict):
        return None
    usage = payload.get('usage') or payload.get('Usage')
    if not isinstance(usage, dict):
        return None
    prompt = usage.get('prompt_tokens') or usage.get('input_tokens') or 0
    completion = usage.get('completion_tokens') or usage.get('output_tokens') or 0
    try:
        prompt = int(prompt)
        completion = int(completion)
    except Exception:
        return None
    if prompt == 0 and completion == 0:
        return None
    return {'prompt_tokens': prompt, 'completion_tokens': completion}


async def record_from_response_dict(
    *, user_id: str, model: str, response_body: dict, request_id: Optional[str] = None
) -> None:
    usage = _extract_usage(response_body or {})
    if not usage:
        return
    await UsageLogs.append(
        user_id=user_id,
        model=model,
        prompt_tokens=usage['prompt_tokens'],
        completion_tokens=usage['completion_tokens'],
        request_id=request_id,
    )


async def record_explicit(
    *, user_id: str, model: str, prompt_tokens: int, completion_tokens: int, request_id: Optional[str] = None
) -> None:
    if prompt_tokens <= 0 and completion_tokens <= 0:
        return
    await UsageLogs.append(
        user_id=user_id,
        model=model,
        prompt_tokens=max(0, prompt_tokens),
        completion_tokens=max(0, completion_tokens),
        request_id=request_id,
    )
