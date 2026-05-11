import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Integer,
    JSON,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context


FREE_PLAN_CODE = 'free'


class Plan(Base):
    __tablename__ = 'plan'

    code = Column(String(32), primary_key=True)
    name = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    monthly_price_cents = Column(Integer, nullable=False, default=0)
    yearly_price_cents = Column(Integer, nullable=True)
    monthly_msg_limit = Column(Integer, nullable=False, default=-1)
    monthly_token_limit = Column(BigInteger, nullable=False, default=-1)
    allowed_model_pattern = Column(Text, nullable=True)
    features_json = Column(JSON, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class PlanModel(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    monthly_price_cents: int = 0
    yearly_price_cents: Optional[int] = None
    monthly_msg_limit: int = -1
    monthly_token_limit: int = -1
    allowed_model_pattern: Optional[str] = None
    features_json: Optional[dict] = None
    display_order: int = 0
    active: bool = True
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class PlansTable:
    async def upsert(self, plan: dict, db: Optional[AsyncSession] = None) -> PlanModel:
        async with get_async_db_context(db) as db:
            now = int(time.time())
            existing = await db.get(Plan, plan['code'])
            if existing is None:
                row = Plan(**{**plan, 'created_at': now, 'updated_at': now})
                db.add(row)
            else:
                for k, v in plan.items():
                    if k == 'code':
                        continue
                    setattr(existing, k, v)
                existing.updated_at = now
                row = existing
            await db.commit()
            await db.refresh(row)
            return PlanModel.model_validate(row)

    async def get_by_code(self, code: str, db: Optional[AsyncSession] = None) -> Optional[PlanModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(Plan, code)
            return PlanModel.model_validate(row) if row else None

    async def list_active(self, db: Optional[AsyncSession] = None) -> list[PlanModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(Plan).where(Plan.active.is_(True)).order_by(Plan.display_order, Plan.monthly_price_cents)
            )
            return [PlanModel.model_validate(r) for r in result.scalars().all()]


Plans = PlansTable()
