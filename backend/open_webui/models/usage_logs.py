import time
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context


class UsageLog(Base):
    __tablename__ = 'usage_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    model = Column(String(128), nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_cents = Column(Integer, nullable=False, default=0)
    request_id = Column(String(64), nullable=True)
    created_at = Column(BigInteger, nullable=False)


class UsageLogModel(BaseModel):
    id: int
    user_id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_cents: int = 0
    request_id: Optional[str] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


def _month_window_start(epoch: Optional[int] = None) -> int:
    """Return epoch seconds for the start of the month containing `epoch`."""
    import datetime as _dt

    now = _dt.datetime.utcfromtimestamp(epoch or int(time.time()))
    start = _dt.datetime(now.year, now.month, 1)
    return int(start.replace(tzinfo=_dt.timezone.utc).timestamp())


class UsageLogsTable:
    async def append(
        self,
        *,
        user_id: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_cents: int = 0,
        request_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            row = UsageLog(
                user_id=user_id,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_cents=cost_cents,
                request_id=request_id,
                created_at=now,
            )
            db.add(row)
            await db.commit()

    async def month_summary(self, user_id: str, db: Optional[AsyncSession] = None) -> dict:
        since = _month_window_start()
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(
                    func.coalesce(func.sum(UsageLog.prompt_tokens), 0),
                    func.coalesce(func.sum(UsageLog.completion_tokens), 0),
                    func.count(UsageLog.id),
                    func.coalesce(func.sum(UsageLog.cost_cents), 0),
                ).where(
                    and_(
                        UsageLog.user_id == user_id,
                        UsageLog.created_at >= since,
                    )
                )
            )
            row = result.first()
            prompt_tokens, completion_tokens, messages, cost_cents = row or (0, 0, 0, 0)
            return {
                'prompt_tokens': int(prompt_tokens or 0),
                'completion_tokens': int(completion_tokens or 0),
                'total_tokens': int((prompt_tokens or 0) + (completion_tokens or 0)),
                'messages': int(messages or 0),
                'cost_cents': int(cost_cents or 0),
                'window_start': since,
            }


UsageLogs = UsageLogsTable()
