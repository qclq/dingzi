"""Measure the history endpoint against a disposable SQLite database.

This is a local regression baseline, not evidence of MySQL or 50-user acceptance.
"""

import asyncio
import os
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.detection import Detection


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    async with sessions() as session:
        for offset in range(0, 100_000, 1_000):
            session.add_all([Detection(image_id=f"bench-{index}", captured_at=start + timedelta(seconds=index), result="NG" if index % 2 else "PASS", image_path="/tmp/benchmark.png") for index in range(offset, offset + 1_000)])
            await session.commit()
    from app.repositories.detection import list_detections
    timings: list[float] = []
    async with sessions() as session:
        for _ in range(100):
            began = time.perf_counter()
            await list_detections(session, start_time=None, end_time=None, result="NG", operator=None, image_id=None, line_id=None, page=1000, page_size=100)
            timings.append((time.perf_counter() - began) * 1_000)
    print({"database": "SQLite in-memory", "samples": len(timings), "p50_ms": round(statistics.median(timings), 2), "p95_ms": round(sorted(timings)[94], 2)})
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
