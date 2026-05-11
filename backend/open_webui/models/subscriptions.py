import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    plan_code = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default='active')
    started_at = Column(BigInteger, nullable=False)
    expires_at = Column(BigInteger, nullable=False)
    auto_renew = Column(Boolean, nullable=False, default=False)
    source_order_id = Column(String, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class SubscriptionModel(BaseModel):
    id: str
    user_id: str
    plan_code: str
    status: str = 'active'
    started_at: int
    expires_at: int
    auto_renew: bool = False
    source_order_id: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class SubscriptionsTable:
    async def get_active_for_user(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[SubscriptionModel]:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.status == 'active',
                        Subscription.expires_at >= now,
                    )
                )
                .order_by(Subscription.expires_at.desc())
                .limit(1)
            )
            row = result.scalars().first()
            return SubscriptionModel.model_validate(row) if row else None

    async def grant_or_extend(
        self,
        *,
        user_id: str,
        plan_code: str,
        seconds: int,
        source_order_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> SubscriptionModel:
        """If an active subscription exists for the same plan, extend it; else create a new one."""
        now = int(time.time())
        async with get_async_db_context(db) as db:
            existing = await self.get_active_for_user(user_id, db=db)
            if existing and existing.plan_code == plan_code:
                row = await db.get(Subscription, existing.id)
                row.expires_at = max(row.expires_at, now) + seconds
                row.updated_at = now
                if source_order_id:
                    row.source_order_id = source_order_id
                await db.commit()
                await db.refresh(row)
                return SubscriptionModel.model_validate(row)

            row = Subscription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_code=plan_code,
                status='active',
                started_at=now,
                expires_at=now + seconds,
                auto_renew=False,
                source_order_id=source_order_id,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return SubscriptionModel.model_validate(row)


Subscriptions = SubscriptionsTable()
