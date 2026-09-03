from app.core.config import Settings
from app.repositories.health import check_database


async def collect_health(settings: Settings, session, redis_client) -> dict:
    database_ok, database_detail = await check_database(session)
    redis_ok = True
    redis_detail = None
    try:
        await redis_client.ping()
    except Exception as exc:  # noqa: BLE001
        redis_ok = False
        redis_detail = str(exc)
    return {
        "database": {"status": "ok" if database_ok else "error", "detail": database_detail},
        "redis": {"status": "ok" if redis_ok else "error", "detail": redis_detail},
    }

