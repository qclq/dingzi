from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.system import PasswordResetRequest
from app.models.user import User
from app.repositories.audit import record_audit
from app.repositories.auth import find_refresh_token, revoke_refresh_token
from app.schemas.auth import AuthResponse, LoginRequest, PasswordResetConfirm, RefreshRequest
from app.security.auth import decode_token, hash_password, token_hash
from app.services.auth import login as login_service
from app.services.auth import refresh as refresh_service

router = APIRouter(prefix="/auth", tags=["auth"])


def trace_id() -> str:
    return str(uuid4())


@router.post("/login", response_model=AuthResponse)
async def login(request: Request, body: LoginRequest, session: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> AuthResponse:
    data = await login_service(session, settings, body, request.client.host if request.client else None)
    return AuthResponse(message="登录成功", data=data, trace_id=trace_id())


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, body: RefreshRequest, session: AsyncSession = Depends(get_db), settings: Settings = Depends(get_settings)) -> AuthResponse:
    data = await refresh_service(session, settings, body.refresh_token, request.client.host if request.client else None)
    return AuthResponse(message="令牌刷新成功", data=data, trace_id=trace_id())


@router.post("/logout")
async def logout(
    request: Request,
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if body and body.refresh_token:
        try:
            payload = decode_token(settings, body.refresh_token, "refresh")
        except HTTPException:
            payload = None
        if payload and payload.get("sub") == str(user.id):
            record = await find_refresh_token(session, token_hash(payload["jti"]))
            if record:
                await revoke_refresh_token(session, record)
    await record_audit(session, user.id, "logout", request.client.host if request.client else None)
    await session.commit()
    return {"code": "SUCCESS", "message": "登出成功", "trace_id": trace_id()}


@router.post("/password-reset/confirm")
async def confirm_password_reset(body: PasswordResetConfirm, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    request = await session.scalar(select(PasswordResetRequest).where(PasswordResetRequest.token_hash == token_hash(body.token)))
    now = datetime.now(UTC)
    if request is None or request.consumed_at is not None or request.expires_at < now:
        raise HTTPException(status_code=400, detail="重置链接无效或已过期")
    user = await session.get(User, request.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=400, detail="用户不可用")
    try: user.password_hash = hash_password(body.password)
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    user.credential_version += 1; request.consumed_at = now
    await record_audit(session, user.id, "password_reset_completed", None)
    await session.commit()
    return {"code": "SUCCESS", "message": "密码已重置"}
