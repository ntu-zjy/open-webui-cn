"""Phone-number + SMS verification code authentication.

Endpoints (all relative to the mount prefix in main.py):
  GET  /captcha           - issue an image captcha (token + data URL)
  POST /send              - send an SMS code (requires solved captcha)
  POST /signin            - sign in or sign up with phone + code (no password)
  POST /bind              - bind a phone number to the currently-logged-in user

The actual user record is created via the existing `signup_handler`, so the
hot path of upstream `auths.py` stays untouched and rebases cleanly.
"""
import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import WEBUI_AUTH, ENABLE_INITIAL_ADMIN_SIGNUP
from open_webui.internal.db import get_async_session
from open_webui.models.users import Users
from open_webui.models.verification_codes import VerificationCodes, generate_numeric_code
from open_webui.routers.auths import SessionUserResponse, create_session_response, signup_handler
from open_webui.utils.auth import get_verified_user
from open_webui.utils.captcha import issue_captcha, verify_captcha
from open_webui.utils.rate_limit import RateLimiter
from open_webui.utils.redis import get_redis_client
from open_webui.utils.sms import get_sms_provider

log = logging.getLogger(__name__)
router = APIRouter()


# Phone-format validation: mainland China (+86) primary; allow +<digits> length 7-15.
_CN_PHONE_RE = re.compile(r'^1[3-9]\d{9}$')
_INTL_PHONE_RE = re.compile(r'^\+?[1-9]\d{6,14}$')


def _normalize_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    phone = phone.strip().replace(' ', '').replace('-', '')
    if _CN_PHONE_RE.match(phone):
        return phone
    if _INTL_PHONE_RE.match(phone):
        return phone
    return None


# --- Rate limiters ---------------------------------------------------------
# 1 send / 60s per phone
_per_phone_60s = RateLimiter(redis_client=get_redis_client(), limit=1, window=60, bucket_size=10)
# 5 sends / hour per IP
_per_ip_hour = RateLimiter(redis_client=get_redis_client(), limit=5, window=3600, bucket_size=60)
# 5 verify attempts / 3 minutes per phone
_verify_limiter = RateLimiter(redis_client=get_redis_client(), limit=5, window=180, bucket_size=30)


# --- Request schemas -------------------------------------------------------


class SendCodeForm(BaseModel):
    phone: str
    scene: str = 'signin'
    captcha_token: str
    captcha_answer: str

    @field_validator('scene')
    @classmethod
    def _check_scene(cls, v: str) -> str:
        if v not in {'signin', 'bind'}:
            raise ValueError('invalid scene')
        return v


class SmsSigninForm(BaseModel):
    phone: str
    code: str


class SmsBindForm(BaseModel):
    phone: str
    code: str


# --- Endpoints -------------------------------------------------------------


@router.get('/captcha')
async def get_captcha():
    return issue_captcha()


@router.post('/send')
async def send_code(request: Request, form_data: SendCodeForm):
    phone = _normalize_phone(form_data.phone)
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid phone format')

    if not verify_captcha(form_data.captcha_token, form_data.captcha_answer):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Captcha verification failed')

    if _per_phone_60s.is_limited(f'sms:send:phone:{phone}'):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail='请求过于频繁，请 60 秒后再试')

    client_ip = request.client.host if request.client else 'unknown'
    if _per_ip_hour.is_limited(f'sms:send:ip:{client_ip}'):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail='IP 请求次数过多，请稍后再试')

    code = generate_numeric_code(6)
    await VerificationCodes.create(
        target=phone, channel='sms', scene=form_data.scene, code=code
    )

    provider = get_sms_provider()
    ok = await provider.send_code(phone, code)
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail='短信发送失败，请稍后重试')

    return {'success': True, 'expires_in': 5 * 60}


@router.post('/signin', response_model=SessionUserResponse)
async def sms_signin(
    request: Request,
    response: Response,
    form_data: SmsSigninForm,
    db: AsyncSession = Depends(get_async_session),
):
    phone = _normalize_phone(form_data.phone)
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid phone format')

    if _verify_limiter.is_limited(f'sms:verify:{phone}'):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail='验证尝试过多，请 3 分钟后再试')

    ok = await VerificationCodes.verify_and_consume(target=phone, scene='signin', code=form_data.code, db=db)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='验证码错误或已过期')

    user = await Users.get_user_by_phone(phone, db=db)
    if user is None:
        if WEBUI_AUTH:
            has_users = await Users.has_users(db=db)
            if not request.app.state.config.ENABLE_SIGNUP and (has_users or not ENABLE_INITIAL_ADMIN_SIGNUP):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
        synthetic_email = f'{uuid.uuid4().hex}@phone.local'
        display_name = f'用户{phone[-4:]}'
        user = await signup_handler(
            request,
            email=synthetic_email,
            password=None,
            name=display_name,
            phone=phone,
            db=db,
        )

    return await create_session_response(request, user, db, response, set_cookie=True)


@router.post('/bind')
async def sms_bind(
    request: Request,
    form_data: SmsBindForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    phone = _normalize_phone(form_data.phone)
    if not phone:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid phone format')

    if _verify_limiter.is_limited(f'sms:verify:{phone}'):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail='验证尝试过多，请 3 分钟后再试')

    existing = await Users.get_user_by_phone(phone, db=db)
    if existing and existing.id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='该手机号已被其他账号绑定')

    ok = await VerificationCodes.verify_and_consume(target=phone, scene='bind', code=form_data.code, db=db)
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='验证码错误或已过期')

    await Users.update_user_by_id(user.id, {'phone': phone}, db=db)
    return {'success': True, 'phone': phone}
