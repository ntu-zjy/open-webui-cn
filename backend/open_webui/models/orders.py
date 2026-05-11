import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context


ORDER_TTL_SECONDS = 30 * 60


class Order(Base):
    __tablename__ = 'order'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    plan_code = Column(String(32), nullable=False)
    period = Column(String(16), nullable=False, default='monthly')
    amount_cents = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default='pending', index=True)
    provider = Column(String(16), nullable=False, default='zpay')
    provider_pay_type = Column(String(16), nullable=True)
    provider_trade_no = Column(String(64), nullable=True, index=True)
    paid_at = Column(BigInteger, nullable=True)
    expires_at = Column(BigInteger, nullable=False)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class OrderModel(BaseModel):
    id: str
    user_id: str
    plan_code: str
    period: str = 'monthly'
    amount_cents: int
    status: str = 'pending'
    provider: str = 'zpay'
    provider_pay_type: Optional[str] = None
    provider_trade_no: Optional[str] = None
    paid_at: Optional[int] = None
    expires_at: int
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class OrdersTable:
    async def create(
        self,
        *,
        user_id: str,
        plan_code: str,
        period: str,
        amount_cents: int,
        provider: str = 'zpay',
        provider_pay_type: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> OrderModel:
        now = int(time.time())
        row = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_code=plan_code,
            period=period,
            amount_cents=amount_cents,
            status='pending',
            provider=provider,
            provider_pay_type=provider_pay_type,
            expires_at=now + ORDER_TTL_SECONDS,
            created_at=now,
            updated_at=now,
        )
        async with get_async_db_context(db) as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return OrderModel.model_validate(row)

    async def get_by_id(self, order_id: str, db: Optional[AsyncSession] = None) -> Optional[OrderModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Order, order_id)
            return OrderModel.model_validate(row) if row else None

    async def mark_paid(
        self,
        *,
        order_id: str,
        provider_trade_no: str,
        provider_pay_type: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> tuple[Optional[OrderModel], bool]:
        """Idempotent. Returns (order, newly_paid).

        newly_paid=True iff this call performed the pending->paid transition,
        which is the signal the caller should use to grant subscription time.
        """
        now = int(time.time())
        async with get_async_db_context(db) as db:
            row = await db.get(Order, order_id)
            if row is None:
                return None, False
            if row.status == 'paid':
                return OrderModel.model_validate(row), False
            row.status = 'paid'
            row.provider_trade_no = provider_trade_no
            if provider_pay_type:
                row.provider_pay_type = provider_pay_type
            row.paid_at = now
            row.updated_at = now
            await db.commit()
            await db.refresh(row)
            return OrderModel.model_validate(row), True

    async def expire_overdue(self, db: Optional[AsyncSession] = None) -> int:
        from sqlalchemy import update

        now = int(time.time())
        async with get_async_db_context(db) as db:
            result = await db.execute(
                update(Order)
                .where(and_(Order.status == 'pending', Order.expires_at < now))
                .values(status='expired', updated_at=now)
            )
            await db.commit()
            return result.rowcount or 0

    async def list_for_user(
        self, user_id: str, limit: int = 20, db: Optional[AsyncSession] = None
    ) -> list[OrderModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit)
            )
            return [OrderModel.model_validate(r) for r in result.scalars().all()]


Orders = OrdersTable()
