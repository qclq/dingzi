from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.health import collect_health

router = APIRouter(tags=["health"])


def get_redis(settings: Settings = Depends(get_settings)) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> HealthResponse:
    dependencies = await collect_health(settings, session, redis)
    await redis.aclose()
    healthy = all(item["status"] == "ok" for item in dependencies.values())
    return HealthResponse(status="ok" if healthy else "degraded", service=settings.app_name, dependencies=dependencies)

