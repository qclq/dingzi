from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


async def find_user(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(User.username == username))


async def find_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def find_refresh_token(session: AsyncSession, jti_hash: str) -> RefreshToken | None:
    return await session.scalar(select(RefreshToken).where(RefreshToken.jti_hash == jti_hash))


async def revoke_refresh_token(session: AsyncSession, record: RefreshToken) -> None:
    record.revoked_at = datetime.now(UTC)


async def add_refresh_token(session: AsyncSession, user_id: int, jti_hash: str, expires_at: datetime) -> RefreshToken:
    record = RefreshToken(user_id=user_id, jti_hash=jti_hash, expires_at=expires_at)
    session.add(record)
    return record
