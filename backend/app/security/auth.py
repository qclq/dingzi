import hashlib
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import Settings

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_OPERATOR})


def validate_password_policy(password: str) -> None:
    if len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        raise ValueError("密码至少 8 位且必须包含大小写字母、数字和特殊字符")
    if not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("密码至少 8 位且必须包含大小写字母、数字和特殊字符")


def hash_password(password: str) -> str:
    validate_password_policy(password)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(settings: Settings, user_id: int, role: str, token_type: str, expires_delta: timedelta, credential_version: int = 0) -> tuple[str, str]:
    now = datetime.now(UTC)
    jti = str(uuid4())
    payload = {"sub": str(user_id), "role": role, "cv": credential_version, "typ": token_type, "jti": jti, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), jti


def decode_token(settings: Settings, token: str, expected_type: str) -> dict:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise credentials_error from exc
    if payload.get("typ") != expected_type or not payload.get("sub") or payload.get("role") not in VALID_ROLES:
        raise credentials_error
    return payload
