"""Public billing endpoints: list plans, fetch current subscription + monthly usage.

Order creation and payment callbacks live in routers/payments.py.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import get_async_session
from open_webui.models.plans import FREE_PLAN_CODE, PlanModel, Plans
from open_webui.models.subscriptions import Subscriptions, SubscriptionModel
from open_webui.models.usage_logs import UsageLogs
from open_webui.utils.auth import get_verified_user

router = APIRouter()
log = logging.getLogger(__name__)


class MeResponse(BaseModel):
    plan: Optional[PlanModel] = None
    subscription: Optional[SubscriptionModel] = None
    usage: dict


@router.get('/plans', response_model=list[PlanModel])
async def list_plans(db: AsyncSession = Depends(get_async_session)):
    return await Plans.list_active(db=db)


@router.get('/me', response_model=MeResponse)
async def get_my_billing(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    sub = await Subscriptions.get_active_for_user(user.id, db=db)
    plan_code = sub.plan_code if sub else FREE_PLAN_CODE
    plan = await Plans.get_by_code(plan_code, db=db)
    usage = await UsageLogs.month_summary(user.id, db=db)
    return MeResponse(plan=plan, subscription=sub, usage=usage)
