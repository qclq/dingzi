"""Initialize or rotate the administrator account from environment variables."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.security.auth import hash_password, validate_password_policy


async def main() -> None:
    username = os.getenv("INIT_ADMIN_USERNAME")
    password = os.getenv("INIT_ADMIN_PASSWORD")
    if not username or not password:
        raise SystemExit("INIT_ADMIN_USERNAME and INIT_ADMIN_PASSWORD are required")
    validate_password_policy(password)
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user is None:
            user = User(username=username, password_hash=hash_password(password))
            session.add(user)
        else:
            user.password_hash = hash_password(password)
        user.role = "admin"
        user.status = "active"
        user.display_name = os.getenv("INIT_ADMIN_DISPLAY_NAME", user.display_name or username)
        user.email = os.getenv("INIT_ADMIN_EMAIL", user.email)
        await session.commit()
    print(f"Administrator initialized: {username}")


if __name__ == "__main__":
    asyncio.run(main())
