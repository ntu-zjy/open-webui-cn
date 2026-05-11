"""Aliyun SMS provider using the v3 RPC signature over HTTPS.

Avoids the heavyweight alibabacloud SDK; signs requests manually per
https://help.aliyun.com/zh/sms/developer-reference/v3-request-structure
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timezone

import aiohttp

log = logging.getLogger(__name__)


class AliyunSmsProvider:
    HOST = 'dysmsapi.aliyuncs.com'
    ENDPOINT = f'https://{HOST}'
    API_VERSION = '2017-05-25'
    ACTION = 'SendSms'

    def __init__(self) -> None:
        self.access_key_id = os.environ.get('ALIYUN_SMS_ACCESS_KEY_ID', '')
        self.access_key_secret = os.environ.get('ALIYUN_SMS_ACCESS_KEY_SECRET', '')
        self.sign_name = os.environ.get('ALIYUN_SMS_SIGN_NAME', '')
        self.template_code = os.environ.get('ALIYUN_SMS_TEMPLATE_CODE', '')

    def _configured(self) -> bool:
        return all([self.access_key_id, self.access_key_secret, self.sign_name, self.template_code])

    def _sign(self, params: dict[str, str]) -> str:
        sorted_qs = '&'.join(
            f'{urllib.parse.quote(k, safe="~")}={urllib.parse.quote(v, safe="~")}'
            for k, v in sorted(params.items())
        )
        string_to_sign = 'POST&%2F&' + urllib.parse.quote(sorted_qs, safe='~')
        key = (self.access_key_secret + '&').encode()
        digest = hmac.new(key, string_to_sign.encode(), hashlib.sha1).digest()
        return base64.b64encode(digest).decode()

    async def send_code(self, phone: str, code: str) -> bool:
        if not self._configured():
            log.error('[SMS:Aliyun] not fully configured; check ALIYUN_SMS_* env vars')
            return False

        common = {
            'AccessKeyId': self.access_key_id,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'SignatureNonce': secrets.token_hex(16),
            'Timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'Format': 'JSON',
            'Version': self.API_VERSION,
            'Action': self.ACTION,
            'RegionId': 'cn-hangzhou',
            'PhoneNumbers': phone,
            'SignName': self.sign_name,
            'TemplateCode': self.template_code,
            'TemplateParam': json.dumps({'code': code}, ensure_ascii=False),
        }
        signature = self._sign(common)
        common['Signature'] = signature

        body = urllib.parse.urlencode(common)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.ENDPOINT, data=body, headers=headers) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        log.error(f'[SMS:Aliyun] non-JSON response: {text[:200]}')
                        return False
                    if data.get('Code') == 'OK':
                        return True
                    log.error(f'[SMS:Aliyun] failed phone={phone} resp={text[:300]}')
                    return False
        except Exception as e:
            log.error(f'[SMS:Aliyun] request error: {e}')
            return False
