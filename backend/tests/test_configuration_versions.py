import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.configuration import ConfigVersion
from app.models.detection import Detection
from app.models.user import User
from app.security.auth import create_token, hash_password
from app.services import realtime


@pytest.fixture()
def config_client():
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def setup() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            session.add_all([
                User(username="config-admin", password_hash=hash_password("Admin123!"), display_name="管理员", role="admin"),
                User(username="config-operator", password_hash=hash_password("Operator123!"), display_name="操作员", role="operator"),
            ])
            await session.commit()

    asyncio.run(setup())

    async def override_db():
        async with sessions() as session:
            yield session

    def headers(user_id: int, role: str) -> dict[str, str]:
        token, _ = create_token(get_settings(), user_id, role, "access", timedelta(hours=1))
        return {"Authorization": f"Bearer {token}"}

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, sessions, headers(1, "admin"), headers(2, "operator")
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_config_publish_is_immutable_and_audited(config_client) -> None:
    client, sessions, admin_headers, _ = config_client
    initial = client.get("/api/v1/configs/defect_thresholds", headers=admin_headers)
    assert initial.status_code == 200
    body = initial.json()
    value = body["value"]
    value["items"][0]["severity_threshold_mm"] = 3.5
    saved = client.put(
        "/api/v1/configs/defect_thresholds",
        headers={**admin_headers, "X-Confirm-Action": "save"},
        json={"value": value, "draft_revision": body["draft_revision"]},
    )
    assert saved.status_code == 200
    published = client.post(
        "/api/v1/configs/publish",
        headers={**admin_headers, "X-Confirm-Action": "publish", "Idempotency-Key": "config-test-1"},
        json={"draft_revision": saved.json()["draft_revision"]},
    )
    assert published.status_code == 200
    assert published.json()["version"] == "v1.0.0"
    first_payload = published.json()["payload"]
    replay = client.post(
        "/api/v1/configs/publish",
        headers={**admin_headers, "X-Confirm-Action": "publish", "Idempotency-Key": "config-test-1"},
        json={"draft_revision": saved.json()["draft_revision"]},
    )
    assert replay.status_code == 200
    assert replay.json()["version"] == "v1.0.0"

    value["items"][0]["severity_threshold_mm"] = 4.0
    second_draft = client.put(
        "/api/v1/configs/defect_thresholds",
        headers={**admin_headers, "X-Confirm-Action": "save"},
        json={"value": value, "draft_revision": saved.json()["draft_revision"]},
    )
    assert second_draft.status_code == 200
    second = client.post(
        "/api/v1/configs/publish",
        headers={**admin_headers, "X-Confirm-Action": "publish", "Idempotency-Key": "config-test-2"},
        json={"draft_revision": second_draft.json()["draft_revision"]},
    )
    assert second.status_code == 200
    assert second.json()["version"] == "v1.0.1"
    assert client.get("/api/v1/configs/versions/v1.0.0", headers=admin_headers).json()["payload"] == first_payload
    rolled_back = client.post(
        "/api/v1/configs/versions/v1.0.0/rollback",
        headers={**admin_headers, "X-Confirm-Action": "rollback", "Idempotency-Key": "config-test-rollback"},
        json={"draft_revision": second_draft.json()["draft_revision"]},
    )
    assert rolled_back.status_code == 200
    assert rolled_back.json()["version"] == "v1.0.2"
    assert rolled_back.json()["payload"] == first_payload

    async def records() -> tuple[list[ConfigVersion], list[AuditLog]]:
        async with sessions() as session:
            return (await session.scalars(select(ConfigVersion))).all(), (await session.scalars(select(AuditLog))).all()

    versions, audits = asyncio.run(records())
    assert len(versions) == 3
    assert {item.action for item in audits} == {"config_draft_saved", "config_publish", "config_rollback"}
    assert all(item.before_json is not None and item.after_json is not None for item in audits)


def test_config_requires_admin_confirmation_and_valid_draft(config_client) -> None:
    client, _, admin_headers, operator_headers = config_client
    assert client.get("/api/v1/configs/model", headers=operator_headers).status_code == 403
    current = client.get("/api/v1/configs/model", headers=admin_headers).json()
    assert client.put("/api/v1/configs/model", headers=admin_headers, json={"value": current["value"], "draft_revision": current["draft_revision"]}).status_code == 400
    current["value"]["confidence_threshold"] = 0.05
    invalid = client.put(
        "/api/v1/configs/model",
        headers={**admin_headers, "X-Confirm-Action": "save"},
        json={"value": current["value"], "draft_revision": current["draft_revision"]},
    )
    assert invalid.status_code == 422


def test_realtime_detection_keeps_its_published_config_snapshot(config_client, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    client, sessions, admin_headers, _ = config_client
    initial = client.get("/api/v1/configs/defect_thresholds", headers=admin_headers).json()
    first_publish = client.post(
        "/api/v1/configs/publish",
        headers={**admin_headers, "X-Confirm-Action": "publish", "Idempotency-Key": "snapshot-v1"},
        json={"draft_revision": initial["draft_revision"]},
    )
    assert first_publish.status_code == 200

    async def no_redis(*_args) -> None:
        return None

    monkeypatch.setattr(realtime, "SessionLocal", sessions)
    monkeypatch.setattr(realtime.broker, "_publish_redis", no_redis)
    first_image = tmp_path / "ng-snapshot-v1.png"
    first_image.write_bytes(b"phase-6")
    asyncio.run(realtime.process_image(first_image))

    updated = client.get("/api/v1/configs/defect_thresholds", headers=admin_headers).json()
    updated["value"]["items"][0]["severity_threshold_mm"] = 1.0
    saved = client.put(
        "/api/v1/configs/defect_thresholds",
        headers={**admin_headers, "X-Confirm-Action": "save"},
        json={"value": updated["value"], "draft_revision": updated["draft_revision"]},
    )
    second_publish = client.post(
        "/api/v1/configs/publish",
        headers={**admin_headers, "X-Confirm-Action": "publish", "Idempotency-Key": "snapshot-v2"},
        json={"draft_revision": saved.json()["draft_revision"]},
    )
    assert second_publish.status_code == 200
    second_image = tmp_path / "ng-snapshot-v2.png"
    second_image.write_bytes(b"phase-6")
    asyncio.run(realtime.process_image(second_image))

    async def detections() -> list[Detection]:
        async with sessions() as session:
            return (await session.scalars(select(Detection).order_by(Detection.image_id))).all()

    records = asyncio.run(detections())
    assert [(item.config_version, item.config_snapshot["defect_thresholds"]["items"][0]["severity_threshold_mm"]) for item in records] == [("v1.0.0", 2.0), ("v1.0.1", 1.0)]
    first_version = client.get("/api/v1/configs/versions/v1.0.0", headers=admin_headers).json()
    assert first_version["payload"]["defect_thresholds"]["items"][0]["severity_threshold_mm"] == 2.0
