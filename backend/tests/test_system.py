from fastapi.testclient import TestClient

import pytest

from test_auth import client as auth_client  # noqa: F401
from test_auth import login


@pytest.fixture(name="client")
def client_fixture(request: pytest.FixtureRequest) -> TestClient:
    return request.getfixturevalue("auth_client")


def headers(client: TestClient, username: str = "admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)['access_token']}"}


def test_system_management_requires_admin(client: TestClient) -> None:
    assert client.get("/api/v1/system/users", headers=headers(client, "operator")).status_code == 403
    assert client.get("/api/v1/system/audit-logs", headers=headers(client, "operator")).status_code == 403


def test_user_lifecycle_and_file_policy(client: TestClient) -> None:
    admin = headers(client)
    created = client.post("/api/v1/system/users", headers=admin, json={"username": "worker", "password": "Worker123!", "display_name": "Worker", "email": "worker@example.com", "role": "operator"})
    assert created.status_code == 201
    user = created.json()
    assert client.post(f"/api/v1/system/users/{user['id']}/status", headers=admin, json={"status": "disabled"}).status_code == 200
    assert client.post(f"/api/v1/system/users/{user['id']}/unlock", headers=admin).status_code == 200
    policy = client.get("/api/v1/system/file-policy", headers=admin)
    assert policy.status_code == 200
    updated = client.put("/api/v1/system/file-policy", headers=admin, json={"retention_days": 90, "quota_gb": 1, "warning_percent": 80, "revision": policy.json()["revision"]})
    assert updated.status_code == 200
    assert client.get("/api/v1/system/file-policy/usage", headers=admin).status_code == 200


def test_mes_configuration_and_logs_csv(client: TestClient) -> None:
    admin = headers(client)
    current = client.get("/api/v1/system/mes/config", headers=admin).json()
    saved = client.put("/api/v1/system/mes/config", headers=admin, json={"mes_url": "http://example.test/mes", "auth_token": "secret", "auto_report": True, "revision": current["revision"]})
    assert saved.status_code == 200 and saved.json()["token_configured"] is True
    assert client.get("/api/v1/system/logs/audit/csv", headers=admin).status_code == 200


def test_operator_permissions_and_sensitive_mes_token(client: TestClient) -> None:
    admin = headers(client)
    operator = headers(client, "operator")
    current = client.get("/api/v1/system/mes/config", headers=admin).json()
    saved = client.put(
        "/api/v1/system/mes/config",
        headers=admin,
        json={"mes_url": "http://example.test/mes", "auth_token": "not-for-response", "auto_report": False, "revision": current["revision"]},
    )
    assert saved.status_code == 200
    assert "not-for-response" not in saved.text
    for path in ("/api/v1/configs", "/api/v1/system/users", "/api/v1/system/mes/config", "/api/v1/system/audit-logs"):
        assert client.get(path, headers=operator).status_code == 403
    assert client.get("/api/v1/analytics/overview", headers=operator).status_code == 200
    assert client.get("/api/v1/detections", headers=operator).status_code == 200
