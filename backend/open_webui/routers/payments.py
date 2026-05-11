"""Payment routes: create order, query status, handle Zpay callback/return.

Flow:
  1. Frontend POST /payments/create {plan_code, period, pay_type}
     -> server creates order(status=pending) + returns Zpay redirect URL
  2. Browser redirects to Zpay; user pays via Alipay/WeChat
  3. Zpay POSTs notify -> /payments/zpay/notify (server-to-server)
     -> verify signature, idempotently mark order paid, grant subscription
  4. Zpay GETs return -> /payments/zpay/return -> redirect to /billing/success
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.orders import OrderModel, Orders
from open_webui.models.plans import Plans
from open_webui.models.subscriptions import Subscriptions
from open_webui.utils.auth import get_verified_user
from open_webui.utils.billing.zpay import build_pay_redirect, verify_notify

router = APIRouter()
log = logging.getLogger(__name__)


class CreateOrderForm(BaseModel):
    plan_code: str
    period: Literal['monthly', 'yearly'] = 'monthly'
    pay_type: Literal['alipay', 'wxpay'] = 'alipay'


class CreateOrderResponse(BaseModel):
    order: OrderModel
    pay_url: str


@router.post('/create', response_model=CreateOrderResponse)
async def create_order(
    form_data: CreateOrderForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    plan = await Plans.get_by_code(form_data.plan_code, db=db)
    if plan is None or not plan.active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='套餐不存在或已下架')

    if form_data.period == 'yearly':
        amount_cents = plan.yearly_price_cents
        if amount_cents is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='该套餐不支持年付')
    else:
        amount_cents = plan.monthly_price_cents

    if amount_cents <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='免费套餐无需下单')

    order = await Orders.create(
        user_id=user.id,
        plan_code=plan.code,
        period=form_data.period,
        amount_cents=amount_cents,
        provider='zpay',
        provider_pay_type=form_data.pay_type,
        db=db,
    )

    title = f'{plan.name} {form_data.period}'
    pay_url = build_pay_redirect(
        order_id=order.id,
        amount_cents=amount_cents,
        title=title,
        pay_type=form_data.pay_type,
    )
    if not pay_url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail='支付通道未配置')

    return CreateOrderResponse(order=order, pay_url=pay_url)


@router.get('/orders/{order_id}', response_model=OrderModel)
async def get_order(
    order_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    order = await Orders.get_by_id(order_id, db=db)
    if order is None or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail='订单不存在')
    return order


@router.get('/orders', response_model=list[OrderModel])
async def list_orders(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await Orders.list_for_user(user.id, db=db)


def _grant_seconds(period: str) -> int:
    return 365 * 24 * 3600 if period == 'yearly' else 31 * 24 * 3600


@router.post('/zpay/notify')
async def zpay_notify(request: Request, db: AsyncSession = Depends(get_async_session)):
    # Zpay sends application/x-www-form-urlencoded
    form = await request.form()
    data = {k: str(v) for k, v in form.items()}

    if not verify_notify(data):
        log.warning(f'Zpay notify signature failed: {data}')
        return PlainTextResponse('sign_error')

    trade_status = data.get('trade_status', '')
    if trade_status != 'TRADE_SUCCESS':
        return PlainTextResponse('success')

    out_trade_no = data.get('out_trade_no', '')
    trade_no = data.get('trade_no', '')
    pay_type = data.get('type', '')

    if not out_trade_no:
        return PlainTextResponse('missing_order')

    order = await Orders.get_by_id(out_trade_no, db=db)
    if order is None:
        return PlainTextResponse('order_not_found')

    paid, newly_paid = await Orders.mark_paid(
        order_id=out_trade_no,
        provider_trade_no=trade_no,
        provider_pay_type=pay_type,
        db=db,
    )
    if paid is None:
        return PlainTextResponse('order_not_found')

    if newly_paid:
        await Subscriptions.grant_or_extend(
            user_id=paid.user_id,
            plan_code=paid.plan_code,
            seconds=_grant_seconds(paid.period),
            source_order_id=paid.id,
            db=db,
        )
    return PlainTextResponse('success')


@router.get('/zpay/return')
async def zpay_return(request: Request):
    order_id = request.query_params.get('out_trade_no', '')
    return RedirectResponse(url=f'/billing/success?order_id={order_id}')
