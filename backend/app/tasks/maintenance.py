import asyncio

from app.services.system import cleanup_files
from app.tasks import celery_app


@celery_app.task(name="maintenance.cleanup_files")
def cleanup_files_task() -> int:
    from app.db.session import SessionLocal
    async def run() -> int:
        async with SessionLocal() as session: return await cleanup_files(session)
    return asyncio.run(run())


@celery_app.task(name="maintenance.cleanup_logs")
def cleanup_logs_task() -> int:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete

    from app.db.session import SessionLocal
    from app.models.audit_log import AuditLog
    from app.models.system import SystemLog

    async def run() -> int:
        async with SessionLocal() as session:
            now = datetime.now(UTC)
            audit_result = await session.execute(delete(AuditLog).where(AuditLog.created_at < now - timedelta(days=180)))
            system_result = await session.execute(delete(SystemLog).where(SystemLog.created_at < now - timedelta(days=90)))
            await session.commit()
            return int(audit_result.rowcount or 0) + int(system_result.rowcount or 0)
    return asyncio.run(run())
