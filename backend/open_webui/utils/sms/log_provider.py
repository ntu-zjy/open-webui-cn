import logging

log = logging.getLogger(__name__)


class LogSmsProvider:
    """Dev/test stub: logs the code instead of sending. Never use in production."""

    async def send_code(self, phone: str, code: str) -> bool:
        log.warning(f'[SMS:LOG] To {phone}, code={code} (no real SMS sent — set SMS_PROVIDER=aliyun)')
        return True
