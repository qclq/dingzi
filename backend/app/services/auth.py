from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.repositories.audit import record_audit
from app.repositories.auth import (
    add_refresh_token,
    find_refresh_token,
    find_user,
    find_user_by_id,
    revoke_refresh_token,
)
from app.schemas.auth import LoginRequest, TokenData, UserInfo
from app.security.auth import create_token, decode_token, token_hash, verify_password

MAX_LOGIN_FAILURES = 5
LOCK_MINUTES = 30


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def user_info(user) -> UserInfo:
    return UserInfo(user_id=user.id, username=user.username, display_name=user.display_name, role=user.role, avatar_url=user.avatar_url)


def _auth_error(detail: str, code: str = "AUTHENTICATION_FAILED", status_code: int = status.HTTP_401_UNAUTHORIZED) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": detail})


async def login(session: AsyncSession, settings: Settings, request: LoginRequest, ip_address: str | None) -> TokenData:
    user = await find_user(session, request.username)
    now = datetime.now(UTC)
    if user is None:
        raise _auth_error("用户名或密码错误")
    if user.status != "active":
        raise _auth_error("账号已停用", "ACCOUNT_DISABLED", status.HTTP_403_FORBIDDEN)
    if (_locked_until := _utc(user.locked_until)) and _locked_until > now:
        raise _auth_error("账号已锁定，请 30 分钟后重试", "ACCOUNT_LOCKED", status.HTTP_423_LOCKED)
    if not verify_password(request.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_LOGIN_FAILURES:
            user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            user.failed_login_attempts = 0
            await record_audit(session, user.id, "account_locked", ip_address)
            await session.commit()
            raise _auth_error("账号已锁定，请 30 分钟后重试", "ACCOUNT_LOCKED", status.HTTP_423_LOCKED)
        await record_audit(session, user.id, "login_failed", ip_address)
        await session.commit()
        raise _auth_error("用户名或密码错误")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now
    access, _ = create_token(settings, user.id, user.role, "access", timedelta(minutes=settings.access_token_expire_minutes), user.credential_version)
    refresh, refresh_jti = create_token(settings, user.id, user.role, "refresh", timedelta(days=settings.refresh_token_expire_days), user.credential_version)
    await add_refresh_token(session, user.id, token_hash(refresh_jti), now + timedelta(days=settings.refresh_token_expire_days))
    await record_audit(session, user.id, "login_success", ip_address)
    await session.commit()
    return TokenData(access_token=access, refresh_token=refresh, expires_in=settings.access_token_expire_minutes * 60, user_info=user_info(user))


async def refresh(session: AsyncSession, settings: Settings, refresh_token: str, ip_address: str | None) -> TokenData:
    payload = decode_token(settings, refresh_token, "refresh")
    record = await find_refresh_token(session, token_hash(payload["jti"]))
    now = datetime.now(UTC)
    if record is None or record.revoked_at is not None or _utc(record.expires_at) <= now:
        raise _auth_error("刷新令牌无效或已撤销", "REFRESH_TOKEN_INVALID")
    user = await find_user_by_id(session, int(payload["sub"]))
    if user is None or user.status != "active":
        raise _auth_error("用户不可用", "ACCOUNT_DISABLED", status.HTTP_403_FORBIDDEN)
    await revoke_refresh_token(session, record)
    access, _ = create_token(settings, user.id, user.role, "access", timedelta(minutes=settings.access_token_expire_minutes), user.credential_version)
    new_refresh, refresh_jti = create_token(settings, user.id, user.role, "refresh", timedelta(days=settings.refresh_token_expire_days), user.credential_version)
    await add_refresh_token(session, user.id, token_hash(refresh_jti), now + timedelta(days=settings.refresh_token_expire_days))
    await record_audit(session, user.id, "token_refreshed", ip_address)
    await session.commit()
    return TokenData(access_token=access, refresh_token=new_refresh, expires_in=settings.access_token_expire_minutes * 60, user_info=user_info(user))


