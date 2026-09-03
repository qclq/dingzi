from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.security.auth import create_token, hash_password


@pytest.fixture()
def client():
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def setup() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)  # test-only isolated schema
        async with sessions() as session:
            session.add_all([
                User(username="admin", password_hash=hash_password("Admin123!"), display_name="管理员", role="admin"),
                User(username="operator", password_hash=hash_password("Operator123!"), display_name="操作员", role="operator"),
            ])
            await session.commit()

    asyncio.run(setup())

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def login(client: TestClient, username: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": username.title() + "123!"})
    assert response.status_code == 200
    return response.json()["data"]


def test_login_success(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin123!"})
    assert response.status_code == 200
    assert response.json()["data"]["user_info"]["role"] == "admin"
    assert response.json()["data"]["expires_in"] == 8 * 60 * 60


def test_login_wrong_password(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Wrong123!"})
    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "用户名或密码错误"


def test_account_lock(client: TestClient) -> None:
    for _ in range(4):
        assert client.post("/api/v1/auth/login", json={"username": "operator", "password": "Wrong123!"}).status_code == 401
    locked = client.post("/api/v1/auth/login", json={"username": "operator", "password": "Wrong123!"})
    assert locked.status_code == 423
    assert client.post("/api/v1/auth/login", json={"username": "operator", "password": "Operator123!"}).status_code == 423


def test_refresh_token(client: TestClient) -> None:
    data = login(client, "admin")
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
    old = client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert old.status_code == 401


def test_logout(client: TestClient) -> None:
    data = login(client, "admin")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    response = client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": data["refresh_token"]})
    assert response.status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}).status_code == 401


def test_admin_permission(client: TestClient) -> None:
    data = login(client, "admin")
    response = client.get("/api/v1/system/admin-check", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 200


def test_operator_permission(client: TestClient) -> None:
    data = login(client, "operator")
    response = client.get("/api/v1/system/admin-check", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert response.status_code == 403


def test_expired_token(client: TestClient) -> None:
    settings = get_settings()
    token, _ = create_token(settings, 1, "admin", "access", timedelta(seconds=-1))
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
