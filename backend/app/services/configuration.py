import copy
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import ConfigurationState, ConfigVersion
from app.models.user import User

CONFIG_TYPES = ("defect_thresholds", "judgment_rules", "roi", "calibration", "camera_light", "model")


def default_payload() -> dict[str, Any]:
    return {
        "defect_thresholds": {
            "items": [
                {"type": "scratch", "severity_threshold_mm": 2.0, "minor_enabled": True, "severe_enabled": True},
                {"type": "pitted_surface", "severity_threshold_mm": 2.0, "minor_enabled": True, "severe_enabled": True},
            ]
        },
        "judgment_rules": {
            "items": [
                {"type": "scratch", "level": "severe", "enabled": True, "max_count": 1},
                {"type": "scratch", "level": "minor", "enabled": True, "max_count": 5},
                {"type": "pitted_surface", "level": "severe", "enabled": True, "max_count": 4},
                {"type": "pitted_surface", "level": "minor", "enabled": True, "max_count": 9},
            ]
        },
        "roi": {"areas": []},
        "calibration": {"mm_per_pixel": 0.1},
        "camera_light": {
            "active_profile_id": "default",
            "profiles": [{"id": "default", "product_model": "default", "exposure": 1000, "gain": 1.0, "trigger_mode": "software", "light_brightness": 50}],
        },
        "model": {"confidence_threshold": 0.5, "nms_threshold": 0.45, "device": "CPU", "model_version": "mock-v1"},
    }


def _as_decimal(value: Any, name: str, lower: str, upper: str) -> None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} 必须为数字") from None
    if number < Decimal(lower) or number > Decimal(upper) or number.as_tuple().exponent < -2:
        raise ValueError(f"{name} 必须在 {lower} 到 {upper} 之间且最多两位小数")


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(payload) != set(CONFIG_TYPES):
        return ["配置包必须包含且仅包含六类配置"]
    thresholds = payload["defect_thresholds"].get("items", [])
    if len(thresholds) != 2 or {item.get("type") for item in thresholds} != {"scratch", "pitted_surface"}:
        errors.append("缺陷阈值必须包含划痕和点蚀")
    for item in thresholds:
        try:
            _as_decimal(item.get("severity_threshold_mm"), "缺陷阈值", "0", "100")
        except ValueError as exc:
            errors.append(str(exc))
        if not isinstance(item.get("minor_enabled"), bool) or not isinstance(item.get("severe_enabled"), bool):
            errors.append("缺陷阈值启用状态必须为布尔值")
        elif not item["minor_enabled"] and not item["severe_enabled"]:
            errors.append(f"{item.get('type')} 至少启用一个缺陷等级")
    rules = payload["judgment_rules"].get("items", [])
    expected_rules = {(kind, level) for kind in ("scratch", "pitted_surface") for level in ("minor", "severe")}
    if len(rules) != 4 or {(item.get("type"), item.get("level")) for item in rules} != expected_rules:
        errors.append("图片合格判定必须包含四条类型×等级规则")
    for item in rules:
        if not isinstance(item.get("enabled"), bool) or not isinstance(item.get("max_count"), int) or item.get("max_count", 0) < 1:
            errors.append("判定规则的 enabled 和 max_count 无效")
    areas = payload["roi"].get("areas", [])
    if not isinstance(areas, list) or len(areas) > 8:
        errors.append("ROI 最多保存 8 个区域")
    for area in areas:
        if any(not isinstance(area.get(key), int) or area[key] < 0 for key in ("x", "y", "width", "height")) or area.get("width", 0) == 0 or area.get("height", 0) == 0:
            errors.append("ROI 必须为非负像素坐标且宽高大于 0")
    try:
        _as_decimal(payload["calibration"].get("mm_per_pixel"), "mm_per_pixel", "0.000001", "100")
    except ValueError as exc:
        errors.append(str(exc))
    camera = payload["camera_light"]
    profiles = camera.get("profiles", [])
    if not profiles or not isinstance(profiles, list) or camera.get("active_profile_id") not in {item.get("id") for item in profiles}:
        errors.append("相机/光源必须至少有一个已应用方案")
    for item in profiles:
        if not all(item.get(key) not in (None, "") for key in ("id", "product_model", "trigger_mode")):
            errors.append("相机方案缺少必要字段")
        if not isinstance(item.get("exposure"), (int, float)) or item["exposure"] < 0 or not isinstance(item.get("gain"), (int, float)) or item["gain"] < 0 or not isinstance(item.get("light_brightness"), (int, float)) or not 0 <= item["light_brightness"] <= 100:
            errors.append("相机/光源数值无效")
    model = payload["model"]
    for key, lower, upper in (("confidence_threshold", "0.1", "0.99"), ("nms_threshold", "0.1", "0.9")):
        try:
            _as_decimal(model.get(key), key, lower, upper)
        except ValueError as exc:
            errors.append(str(exc))
    if model.get("device") not in {"CPU", "GPU"} or not isinstance(model.get("model_version"), str) or not model["model_version"].strip():
        errors.append("模型设备或模型版本无效")
    return errors


async def state_for_update(session: AsyncSession) -> ConfigurationState:
    state = await session.scalar(select(ConfigurationState).where(ConfigurationState.id == 1).with_for_update())
    if state is None:
        state = ConfigurationState(id=1, draft_payload=default_payload(), draft_revision=1)
        session.add(state)
        await session.flush()
    return state


async def state_for_read(session: AsyncSession) -> ConfigurationState:
    state = await session.get(ConfigurationState, 1)
    if state is None:
        state = await state_for_update(session)
        await session.commit()
    return state


def client_ip(request_headers: dict[str, str], fallback: str | None) -> str | None:
    forwarded = request_headers.get("x-forwarded-for")
    return forwarded.split(",", 1)[0].strip() if forwarded else fallback


def add_audit(session: AsyncSession, actor: User, action: str, resource: str, before: dict | None, after: dict | None, ip: str | None, version: str | None = None) -> None:
    from app.models.audit_log import AuditLog

    session.add(AuditLog(actor_id=actor.id, action=action, resource=resource, before_json=before, after_json=after, ip_address=ip, config_version=version))


async def current_published_config(session: AsyncSession) -> tuple[str, dict[str, Any]]:
    state = await state_for_read(session)
    if state.published_version:
        record = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == state.published_version))
        if record is not None:
            return record.version, copy.deepcopy(record.payload_json)
    # Bootstrap creates the only mutable-to-immutable transition for a new installation.
    record = ConfigVersion(version="v1.0.0", payload_json=copy.deepcopy(state.draft_payload), published_at=datetime.now(UTC))
    session.add(record)
    state.published_version = record.version
    await session.commit()
    return record.version, copy.deepcopy(record.payload_json)


def next_version(previous: str | None) -> str:
    if previous is None:
        return "v1.0.0"
    try:
        return f"v1.0.{int(previous.rsplit('.', 1)[1]) + 1}"
    except (IndexError, ValueError):
        return "v1.0.0"


def require_confirmation(value: str | None, action: str) -> None:
    if value != action:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"重要操作需要 X-Confirm-Action: {action}")
