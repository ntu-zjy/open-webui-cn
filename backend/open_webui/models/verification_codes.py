import hashlib
import secrets
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.internal.db import Base, get_async_db_context


class VerificationCode(Base):
    __tablename__ = 'verification_code'

    id = Column(String, primary_key=True)
    target = Column(String(128), nullable=False)
    channel = Column(String(16), nullable=False)
    scene = Column(String(32), nullable=False)
    code_hash = Column(String(128), nullable=False)
    expires_at = Column(BigInteger, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    consumed_at = Column(BigInteger, nullable=True)
    created_at = Column(BigInteger, nullable=False)


class VerificationCodeModel(BaseModel):
    id: str
    target: str
    channel: str
    scene: str
    code_hash: str
    expires_at: int
    attempts: int
    consumed_at: Optional[int] = None
    created_at: int

    model_config = ConfigDict(from_attributes=True)


def _hash_code(code: str, target: str) -> str:
    return hashlib.sha256(f'{target}:{code}'.encode()).hexdigest()


def generate_numeric_code(length: int = 6) -> str:
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


CODE_TTL_SECONDS = 5 * 60
MAX_ATTEMPTS = 5


class VerificationCodesTable:
    async def create(
        self,
        *,
        target: str,
        channel: str,
        scene: str,
        code: str,
        ttl_seconds: int = CODE_TTL_SECONDS,
        db: Optional[AsyncSession] = None,
    ) -> VerificationCodeModel:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            # Invalidate prior unconsumed codes for the same (target, scene)
            await db.execute(
                update(VerificationCode)
                .where(
                    and_(
                        VerificationCode.target == target,
                        VerificationCode.scene == scene,
                        VerificationCode.consumed_at.is_(None),
                    )
                )
                .values(consumed_at=now)
            )
            row = VerificationCode(
                id=str(uuid.uuid4()),
                target=target,
                channel=channel,
                scene=scene,
                code_hash=_hash_code(code, target),
                expires_at=now + ttl_seconds,
                attempts=0,
                consumed_at=None,
                created_at=now,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return VerificationCodeModel.model_validate(row)

    async def verify_and_consume(
        self,
        *,
        target: str,
        scene: str,
        code: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(VerificationCode)
                .where(
                    and_(
                        VerificationCode.target == target,
                        VerificationCode.scene == scene,
                        VerificationCode.consumed_at.is_(None),
                        VerificationCode.expires_at >= now,
                    )
                )
                .order_by(VerificationCode.created_at.desc())
                .limit(1)
            )
            row = result.scalars().first()
            if not row:
                return False

            if row.attempts >= MAX_ATTEMPTS:
                row.consumed_at = now
                await db.commit()
                return False

            if row.code_hash != _hash_code(code, target):
                row.attempts = row.attempts + 1
                await db.commit()
                return False

            row.consumed_at = now
            await db.commit()
            return True

    async def latest_unconsumed(
        self,
        *,
        target: str,
        scene: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[VerificationCodeModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(VerificationCode)
                .where(
                    and_(
                        VerificationCode.target == target,
                        VerificationCode.scene == scene,
                        VerificationCode.consumed_at.is_(None),
                    )
                )
                .order_by(VerificationCode.created_at.desc())
                .limit(1)
            )
            row = result.scalars().first()
            return VerificationCodeModel.model_validate(row) if row else None

    async def purge_expired(self, db: Optional[AsyncSession] = None) -> int:
        now = int(time.time())
        async with get_async_db_context(db) as db:
            result = await db.execute(
                delete(VerificationCode).where(VerificationCode.expires_at < now - 24 * 3600)
            )
            await db.commit()
            return result.rowcount or 0


VerificationCodes = VerificationCodesTable()
