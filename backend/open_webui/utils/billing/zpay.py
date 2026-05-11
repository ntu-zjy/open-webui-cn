"""Zpay (z-pay.cn) aggregator signing / verification.

Zpay's official protocol uses MD5 signing over the URL-encoded form fields,
sorted by key, with the merchant key appended (NOT included as `key=`).
See https://z-pay.cn/doc.html

Required env:
    ZPAY_PID, ZPAY_KEY
Optional:
    ZPAY_API_BASE (default https://z-pay.cn)
    ZPAY_NOTIFY_URL, ZPAY_RETURN_URL
"""
import hashlib
import logging
import os
import urllib.parse
from typing import Optional
from urllib.parse import quote

log = logging.getLogger(__name__)


def _sign(params: dict[str, str], key: str) -> str:
    """Zpay rule: filter empty + filter `sign` / `sign_type`, sort by key, urlencode,
    append `&key=<merchant_key>` ONLY for the digest computation, then md5."""
    items = sorted((k, v) for k, v in params.items() if v not in (None, '') and k not in ('sign', 'sign_type'))
    raw = '&'.join(f'{k}={v}' for k, v in items) + key
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def build_pay_redirect(
    *,
    order_id: str,
    amount_cents: int,
    title: str,
    pay_type: str = 'alipay',
    notify_url: Optional[str] = None,
    return_url: Optional[str] = None,
) -> Optional[str]:
    """Build a redirect URL the browser can navigate to for payment.

    Returns None if Zpay is not configured.
    """
    pid = os.environ.get('ZPAY_PID', '').strip()
    key = os.environ.get('ZPAY_KEY', '').strip()
    api_base = os.environ.get('ZPAY_API_BASE', 'https://z-pay.cn').rstrip('/')
    if not pid or not key:
        log.error('Zpay not configured: set ZPAY_PID and ZPAY_KEY')
        return None

    money = f'{amount_cents/100:.2f}'

    params: dict[str, str] = {
        'pid': pid,
        'type': pay_type,
        'out_trade_no': order_id,
        'notify_url': notify_url or os.environ.get('ZPAY_NOTIFY_URL', ''),
        'return_url': return_url or os.environ.get('ZPAY_RETURN_URL', ''),
        'name': title,
        'money': money,
    }
    sign = _sign(params, key)
    params['sign'] = sign
    params['sign_type'] = 'MD5'

    qs = '&'.join(f'{quote(k, safe="")}={quote(str(v), safe="")}' for k, v in params.items())
    return f'{api_base}/submit.php?{qs}'


def verify_notify(form_data: dict) -> bool:
    """Verify a Zpay async callback signature.

    Zpay POSTs form-encoded data; convert request.form() into a plain dict
    (single values) before calling.
    """
    key = os.environ.get('ZPAY_KEY', '').strip()
    if not key:
        return False
    received_sign = form_data.get('sign', '')
    if not received_sign:
        return False
    computed = _sign({k: str(v) for k, v in form_data.items()}, key)
    return computed.lower() == received_sign.lower()
