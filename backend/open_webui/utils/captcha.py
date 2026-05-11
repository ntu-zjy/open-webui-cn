"""Simple image captcha generator using Pillow.

Stores the answer in Redis (or in-memory fallback) keyed by a random token.
The frontend renders the image then submits {token, answer} alongside the
SMS-send request, so bots can't trivially trigger SMS bursts.
"""
import base64
import io
import random
import secrets
import string
import time
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from open_webui.env import REDIS_KEY_PREFIX
from open_webui.utils.redis import get_redis_client


CAPTCHA_TTL_SECONDS = 5 * 60
CAPTCHA_LENGTH = 4
CAPTCHA_CHARSET = string.digits + 'ABCDEFGHJKLMNPQRSTUVWXYZ'  # avoid I/O ambiguity


_memory_store: dict[str, tuple[str, int]] = {}


def _redis_key(token: str) -> str:
    return f'{REDIS_KEY_PREFIX}:captcha:{token}'


def _store_set(token: str, answer: str) -> None:
    r = get_redis_client()
    if r is not None:
        try:
            r.setex(_redis_key(token), CAPTCHA_TTL_SECONDS, answer)
            return
        except Exception:
            pass
    _memory_store[token] = (answer, int(time.time()) + CAPTCHA_TTL_SECONDS)


def _store_pop(token: str) -> Optional[str]:
    r = get_redis_client()
    if r is not None:
        try:
            val = r.get(_redis_key(token))
            if val is None:
                return None
            r.delete(_redis_key(token))
            return val.decode() if isinstance(val, (bytes, bytearray)) else val
        except Exception:
            pass
    entry = _memory_store.pop(token, None)
    if not entry:
        return None
    answer, expires = entry
    if expires < int(time.time()):
        return None
    return answer


def _generate_answer() -> str:
    return ''.join(secrets.choice(CAPTCHA_CHARSET) for _ in range(CAPTCHA_LENGTH))


def _render_image(text: str) -> bytes:
    width, height = 140, 48
    img = Image.new('RGB', (width, height), color=(245, 245, 250))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for i, ch in enumerate(text):
        x = 12 + i * 28 + random.randint(-3, 3)
        y = 10 + random.randint(-4, 4)
        color = (random.randint(0, 120), random.randint(0, 120), random.randint(0, 120))
        draw.text((x, y), ch, fill=color, font=font)

    # noise lines + dots
    for _ in range(4):
        draw.line(
            (random.randint(0, width), random.randint(0, height),
             random.randint(0, width), random.randint(0, height)),
            fill=(random.randint(150, 200),) * 3,
            width=1,
        )
    for _ in range(80):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(100, 200),) * 3,
        )

    img = img.filter(ImageFilter.SMOOTH)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def issue_captcha() -> dict:
    """Return {token, image_data_url}."""
    token = secrets.token_urlsafe(24)
    answer = _generate_answer()
    _store_set(token, answer.lower())
    image_bytes = _render_image(answer)
    b64 = base64.b64encode(image_bytes).decode()
    return {
        'token': token,
        'image': f'data:image/png;base64,{b64}',
        'expires_in': CAPTCHA_TTL_SECONDS,
    }


def verify_captcha(token: str, answer: str) -> bool:
    if not token or not answer:
        return False
    stored = _store_pop(token)
    if stored is None:
        return False
    return stored.strip().lower() == answer.strip().lower()
