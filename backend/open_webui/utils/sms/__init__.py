import logging
import os
from typing import Protocol

log = logging.getLogger(__name__)


class SmsProvider(Protocol):
    async def send_code(self, phone: str, code: str) -> bool: ...


_provider_singleton: SmsProvider | None = None


def get_sms_provider() -> SmsProvider:
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    name = os.environ.get('SMS_PROVIDER', 'log').lower()

    if name == 'aliyun':
        from open_webui.utils.sms.aliyun import AliyunSmsProvider

        _provider_singleton = AliyunSmsProvider()
    else:
        from open_webui.utils.sms.log_provider import LogSmsProvider

        _provider_singleton = LogSmsProvider()

    return _provider_singleton
