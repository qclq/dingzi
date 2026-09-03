import asyncio
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.detection import Defect, Detection
from app.models.system import DetectionFile, MesDelivery
from app.services.analytics import record_detection_analytics
from app.services.configuration import current_published_config
from app.services.decision import DefectResult, decide
from app.services.inference import InferenceProvider, model_runtime, run_inference


class RealtimeBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._latest: dict[str, dict] = {}
        self._sequences: dict[str, int] = defaultdict(int)
        self._redis: Redis | None = None
        self._redis_disabled = False

    async def _publish_redis(self, line_id: str, payload: str) -> None:
        if self._redis_disabled:
            return
        if self._redis is None:
            self._redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        redis_client = self._redis
        try:
            await redis_client.publish(f"realtime:{line_id}", payload)
        except RedisError:
            # Local subscribers keep the demo usable when Redis is not installed.
            self._redis_disabled = True
            await redis_client.aclose()
            if self._redis is redis_client:
                self._redis = None

    def envelope(self, event_type: str, data: dict, line_id: str) -> dict:
        self._sequences[line_id] += 1
        event = {
            "type": event_type,
            "event_id": str(uuid4()),
            "sequence": self._sequences[line_id],
            "occurred_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        if event_type in {"FRAME", "INFER", "DEVICE", "ALERT"}:
            self._latest[line_id] = {**self._latest.get(line_id, {}), event_type.lower(): event}
        return event

    async def publish(self, event_type: str, data: dict, line_id: str) -> dict:
        event = self.envelope(event_type, data, line_id)
        payload = json.dumps(event, ensure_ascii=False)
        for queue in tuple(self._subscribers[line_id]):
            await queue.put(payload)
        await self._publish_redis(line_id, payload)
        return event

    def subscribe(self, line_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers[line_id].add(queue)
        return queue

    def unsubscribe(self, line_id: str, queue: asyncio.Queue[str]) -> None:
        self._subscribers[line_id].discard(queue)

    def latest(self, line_id: str) -> dict:
        return self._latest.get(line_id, {})


broker = RealtimeBroker()


def apply_published_thresholds(defects: list[DefectResult], payload: dict) -> list[DefectResult]:
    """Classify by the frozen length boundary when physical dimensions are available."""
    settings = {item["type"]: item for item in payload["defect_thresholds"]["items"]}
    adjusted: list[DefectResult] = []
    for defect in defects:
        setting = settings.get(defect.type)
        if setting is None or defect.width_mm is None or defect.height_mm is None:
            adjusted.append(defect)
            continue
        level = "minor" if max(defect.width_mm, defect.height_mm) <= setting["severity_threshold_mm"] else "severe"
        if not setting[f"{level}_enabled"]:
            adjusted.append(defect)
            continue
        adjusted.append(DefectResult(defect.type, level, defect.confidence, defect.bbox, defect.width_mm, defect.height_mm))
    return adjusted


def active_rules(payload: dict) -> dict[tuple[str, str], int]:
    return {(item["type"], item["level"]): item["max_count"] for item in payload["judgment_rules"]["items"] if item["enabled"]}


async def process_image(
    image_path: Path,
    line_id: str = "line-1",
    operator: str = "mock-operator",
    provider: InferenceProvider | None = None,
) -> dict:
    captured_at = datetime.now(UTC)
    async with SessionLocal() as configuration_session:
        config_version, config_snapshot = await current_published_config(configuration_session)
    provider = provider or model_runtime.provider()
    defects, inference_ms = run_inference(provider, image_path)
    defects = apply_published_thresholds(defects, config_snapshot)
    result = decide(defects, active_rules(config_snapshot))
    image_id = image_path.stem
    async with SessionLocal() as session:
        existing = await session.scalar(select(Detection).where(Detection.image_id == image_id))
        if existing is not None:
            return {
                "image_id": existing.image_id,
                "line_id": existing.line_id,
                "captured_at": existing.captured_at.isoformat(),
                "operator": existing.operator,
                "defects": [],
                "result": existing.result,
                "image_path": existing.image_path,
                "thumbnail_path": existing.thumbnail_path,
                "model_version": existing.model_version,
                "config_version": existing.config_version,
                "inference_ms": existing.inference_ms,
                "mes_status": existing.mes_status,
            }
        detection = Detection(
            image_id=image_id,
            line_id=line_id,
            captured_at=captured_at,
            operator=operator,
            result=result,
            image_path=str(image_path),
            thumbnail_path=None,
            model_version=provider.model_version,
            config_version=config_version,
            config_snapshot=config_snapshot,
            inference_ms=inference_ms,
            defect_count=len(defects),
            raw_output={"defects": [defect.__dict__ for defect in defects]},
        )
        detection.defects = [
            Defect(
                type=defect.type,
                level=defect.level,
                confidence=defect.confidence,
                bbox=defect.bbox,
                width_mm=defect.width_mm,
                height_mm=defect.height_mm,
            )
            for defect in defects
        ]
        session.add(detection)
        try:
            await session.flush()
            try:
                size_bytes = image_path.stat().st_size
            except OSError:
                size_bytes = 0
            session.add(DetectionFile(detection_id=detection.id, kind="image", uri=str(image_path), size_bytes=size_bytes))
            from app.services.system import DEFAULT_MES, setting
            mes = await setting(session, "mes", DEFAULT_MES)
            if mes.value.get("auto_report"):
                session.add(MesDelivery(detection_id=detection.id, idempotency_key=f"detection:{detection.id}", payload={"image_id": detection.image_id, "result": detection.result, "captured_at": detection.captured_at.isoformat(), "defect_count": detection.defect_count}))
            await record_detection_analytics(session, detection)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return {
                "image_id": image_id,
                "line_id": line_id,
                "captured_at": captured_at.isoformat(),
                "operator": operator,
                "defects": [defect.__dict__ for defect in defects],
                "result": result,
                "image_path": str(image_path),
                "thumbnail_path": None,
                "model_version": provider.model_version,
                "config_version": config_version,
                "inference_ms": inference_ms,
                "mes_status": "not_sent",
            }
    data = {
        "image_id": image_id,
        "line_id": line_id,
        "captured_at": captured_at.isoformat(),
        "operator": operator,
        "defects": [defect.__dict__ for defect in defects],
        "result": result,
        "image_path": str(image_path),
        "thumbnail_path": None,
        "model_version": provider.model_version,
        "config_version": config_version,
        "inference_ms": inference_ms,
        "mes_status": "not_sent",
    }
    await broker.publish("FRAME", {"image_id": image_id, "image_path": str(image_path)}, line_id)
    await broker.publish("INFER", data, line_id)
    return data


async def snapshot(line_id: str) -> dict:
    async with SessionLocal() as session:
        detection = await session.scalar(
            select(Detection)
            .options(selectinload(Detection.defects))
            .where(Detection.line_id == line_id)
            .order_by(Detection.captured_at.desc())
            .limit(1)
        )
        if detection is None:
            return {"line_id": line_id, "latest": None, "events": broker.latest(line_id)}
        return {
            "line_id": line_id,
            "latest": {
                "image_id": detection.image_id,
                "captured_at": detection.captured_at.isoformat(),
                "operator": detection.operator,
                "result": detection.result,
                "defect_count": detection.defect_count,
                "image_path": detection.image_path,
                "thumbnail_path": detection.thumbnail_path,
                "model_version": detection.model_version,
                "config_version": detection.config_version,
                "inference_ms": detection.inference_ms,
                "mes_status": detection.mes_status,
                "defects": [
                    {"type": item.type, "level": item.level, "confidence": item.confidence, "bbox": item.bbox}
                    for item in detection.defects
                ],
            },
            "events": broker.latest(line_id),
        }
