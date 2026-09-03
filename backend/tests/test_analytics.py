import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.health import get_redis
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.detection import Defect, Detection
from app.models.user import User
from app.security.auth import create_token, hash_password
from app.services.analytics import record_detection_analytics


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        assert ex == 60
        self.values[key] = value

    async def aclose(self) -> None:
        return None


@pytest.fixture()
def analytics_client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    cache = FakeRedis()

    async def setup() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as session:
            session.add(
                User(
                    username="analytics-user",
                    password_hash=hash_password("Analytics123!"),
                    display_name="统计测试",
                    role="operator",
                )
            )
            start = datetime(2026, 1, 1, 9, tzinfo=UTC)
            samples = [
                ("analytics-1", start, "PASS", "scratch", "minor", [0.1, 0.2, 0.3, 0.4]),
                ("analytics-2", start + timedelta(hours=2), "NG", "scratch", "severe", [0.2, 0.1, 0.2, 0.2]),
                ("analytics-3", start + timedelta(days=1), "PASS", "pitted_surface", "minor", [0.5, 0.6, 0.2, 0.1]),
            ]
            for image_id, captured_at, result, kind, level, bbox in samples:
                detection = Detection(
                    image_id=image_id,
                    line_id="line-1",
                    captured_at=captured_at,
                    operator="operator-a",
                    result=result,
                    image_path=f"/data/{image_id}.png",
                    defect_count=1,
                )
                detection.defects = [Defect(type=kind, level=level, confidence=0.95, bbox=bbox)]
                session.add(detection)
                await session.flush()
                await record_detection_analytics(session, detection)
            await session.commit()

    asyncio.run(setup())

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: cache
    token, _ = create_token(get_settings(), 1, "operator", "access", timedelta(hours=1))
    with TestClient(app) as client:
        yield client, cache, {"Authorization": f"Bearer {token}"}
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def custom_range() -> dict[str, str]:
    return {
        "period": "custom",
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": "2026-01-02T23:59:59Z",
    }


def test_overview_uses_backend_rate_and_cache(analytics_client) -> None:
    client, cache, headers = analytics_client
    response = client.get("/api/v1/analytics/overview", headers=headers, params=custom_range())

    assert response.status_code == 200
    assert response.json()["total_detections"] == 3
    assert response.json()["ng_detections"] == 1
    assert response.json()["defect_rate"] == 33.33
    assert response.json()["rate_definition"] == "NG 检测记录数 / 检测总数 × 100"
    assert cache.values


def test_trends_distribution_and_heatmap_use_aggregates(analytics_client) -> None:
    client, _, headers = analytics_client
    trends = client.get("/api/v1/analytics/trends", headers=headers, params=custom_range())
    distribution = client.get("/api/v1/analytics/defect-distribution", headers=headers, params=custom_range())
    heatmap = client.get("/api/v1/analytics/heatmap", headers=headers, params=custom_range())

    assert trends.status_code == distribution.status_code == heatmap.status_code == 200
    assert [(item["total_detections"], item["ng_detections"]) for item in trends.json()["items"]] == [(2, 1), (1, 0)]
    counts = {(item["type"], item["level"]): item["count"] for item in distribution.json()["items"]}
    assert counts == {("scratch", "minor"): 1, ("scratch", "severe"): 1, ("pitted_surface", "minor"): 1, ("pitted_surface", "severe"): 0}
    assert heatmap.json()["coordinate_basis"] == "normalized_bbox_center"
    assert sum(item["count"] for item in heatmap.json()["items"]) == 3


def test_analytics_alias_validation_and_authentication(analytics_client) -> None:
    client, _, headers = analytics_client
    assert client.get("/api/v1/analytics/trends").status_code == 401
    assert client.get("/api/v1/analytics/defect-trend", headers=headers, params=custom_range()).status_code == 200
    assert client.get("/api/v1/analytics/overview", headers=headers, params={"period": "custom"}).status_code == 422
    assert client.get(
        "/api/v1/analytics/heatmap",
        headers=headers,
        params={"period": "custom", "start_time": "2026-01-03T00:00:00Z", "end_time": "2026-01-01T00:00:00Z"},
    ).status_code == 422
