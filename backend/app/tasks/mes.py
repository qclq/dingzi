import asyncio

from app.services.system import dispatch_delivery
from app.tasks import celery_app


@celery_app.task(name="mes.deliver", autoretry_for=(), max_retries=0)
def deliver_mes(delivery_id: int) -> None:
    from app.db.session import SessionLocal

    async def run() -> None:
        async with SessionLocal() as session:
            await dispatch_delivery(session, delivery_id)
    asyncio.run(run())
