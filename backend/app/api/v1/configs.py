import copy

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.configuration import ConfigPublishKey, ConfigVersion
from app.models.user import User
from app.schemas.configuration import (
    ConfigDraftResponse,
    ConfigSummaryResponse,
    ConfigTypeUpdate,
    ConfigValidationResponse,
    ConfigVersionResponse,
    PublishRequest,
)
from app.services.configuration import (
    CONFIG_TYPES,
    add_audit,
    client_ip,
    default_payload,
    next_version,
    require_confirmation,
    state_for_read,
    state_for_update,
    validate_payload,
)
from app.services.inference import model_runtime

router = APIRouter(prefix="/configs", tags=["configs"])


def ensure_config_type(config_type: str) -> None:
    if config_type not in CONFIG_TYPES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未知配置类型")


def response_for(config_type: str, state) -> ConfigDraftResponse:
    return ConfigDraftResponse(config_type=config_type, value=copy.deepcopy(state.draft_payload[config_type]), draft_revision=state.draft_revision, published_version=state.published_version)


@router.get("", response_model=ConfigSummaryResponse)
async def summary(user: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ConfigSummaryResponse:
    state = await state_for_read(session)
    return ConfigSummaryResponse(draft_revision=state.draft_revision, published_version=state.published_version, config_types=list(CONFIG_TYPES))


@router.get("/versions", response_model=list[ConfigVersionResponse])
async def versions(user: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> list[ConfigVersionResponse]:
    records = (await session.scalars(select(ConfigVersion).order_by(ConfigVersion.published_at.desc()))).all()
    return [ConfigVersionResponse(version=item.version, payload=item.payload_json, published_at=item.published_at, published_by=item.published_by) for item in records]


@router.get("/versions/{config_version}", response_model=ConfigVersionResponse)
async def version(config_version: str, user: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ConfigVersionResponse:
    item = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == config_version))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")
    return ConfigVersionResponse(version=item.version, payload=item.payload_json, published_at=item.published_at, published_by=item.published_by)


@router.post("/versions/{config_version}/rollback", response_model=ConfigVersionResponse)
async def rollback(
    config_version: str,
    body: PublishRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    confirm_action: str | None = Header(default=None, alias="X-Confirm-Action"),
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db),
) -> ConfigVersionResponse:
    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回滚配置需要 Idempotency-Key")
    require_confirmation(confirm_action, "rollback")
    state = await state_for_update(session)
    if body.draft_revision != state.draft_revision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="草稿已更新，请重新加载后回滚")
    source = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == config_version))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置版本不存在")
    prior_key = await session.scalar(select(ConfigPublishKey).where(ConfigPublishKey.idempotency_key == idempotency_key))
    if prior_key is not None:
        prior = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == prior_key.config_version))
        if prior is not None:
            return ConfigVersionResponse(version=prior.version, payload=prior.payload_json, published_at=prior.published_at, published_by=prior.published_by)
    version_name = next_version(state.published_version)
    restored_payload = copy.deepcopy(source.payload_json)
    record = ConfigVersion(version=version_name, payload_json=restored_payload, published_by=user.id)
    session.add_all([record, ConfigPublishKey(idempotency_key=idempotency_key, config_version=version_name)])
    before = {"published_version": state.published_version}
    state.draft_payload = copy.deepcopy(restored_payload)
    state.draft_revision += 1
    state.published_version = version_name
    state.updated_by = user.id
    add_audit(session, user, "config_rollback", "configs", before, {"published_version": version_name, "source_version": source.version}, client_ip(request.headers, request.client.host if request.client else None), version_name)
    await session.commit()
    await session.refresh(record)
    await model_runtime.hot_switch(record.payload_json["model"], version_name)
    return ConfigVersionResponse(version=record.version, payload=record.payload_json, published_at=record.published_at, published_by=record.published_by)


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate(user: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ConfigValidationResponse:
    state = await state_for_read(session)
    errors = validate_payload(state.draft_payload)
    return ConfigValidationResponse(valid=not errors, errors=errors, draft_revision=state.draft_revision)


@router.post("/publish", response_model=ConfigVersionResponse)
async def publish(
    body: PublishRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    confirm_action: str | None = Header(default=None, alias="X-Confirm-Action"),
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db),
) -> ConfigVersionResponse:
    if not idempotency_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="发布配置需要 Idempotency-Key")
    require_confirmation(confirm_action, "publish")
    state = await state_for_update(session)
    prior_key = await session.scalar(select(ConfigPublishKey).where(ConfigPublishKey.idempotency_key == idempotency_key))
    if prior_key is not None:
        prior = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == prior_key.config_version))
        if prior is not None:
            return ConfigVersionResponse(version=prior.version, payload=prior.payload_json, published_at=prior.published_at, published_by=prior.published_by)
    if body.draft_revision != state.draft_revision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="草稿已更新，请重新加载后发布")
    errors = validate_payload(state.draft_payload)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})
    version_name = next_version(state.published_version)
    record = ConfigVersion(version=version_name, payload_json=copy.deepcopy(state.draft_payload), published_by=user.id)
    session.add(record)
    session.add(ConfigPublishKey(idempotency_key=idempotency_key, config_version=version_name))
    before = {"published_version": state.published_version}
    state.published_version = version_name
    add_audit(session, user, "config_publish", "configs", before, {"published_version": version_name}, client_ip(request.headers, request.client.host if request.client else None), version_name)
    await session.commit()
    await session.refresh(record)
    await model_runtime.hot_switch(record.payload_json["model"], version_name)
    return ConfigVersionResponse(version=record.version, payload=record.payload_json, published_at=record.published_at, published_by=record.published_by)


@router.post("/{config_type}/reset", response_model=ConfigDraftResponse)
async def reset(
    config_type: str,
    request: Request,
    confirm_action: str | None = Header(default=None, alias="X-Confirm-Action"),
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db),
) -> ConfigDraftResponse:
    ensure_config_type(config_type)
    require_confirmation(confirm_action, "reset")
    state = await state_for_update(session)
    before = copy.deepcopy(state.draft_payload[config_type])
    state.draft_payload[config_type] = default_payload()[config_type]
    state.draft_revision += 1
    state.updated_by = user.id
    add_audit(session, user, "config_reset", f"configs/{config_type}", before, state.draft_payload[config_type], client_ip(request.headers, request.client.host if request.client else None), state.published_version)
    await session.commit()
    return response_for(config_type, state)


@router.post("/model/hot-switch")
async def hot_switch_model(
    request: Request,
    confirm_action: str | None = Header(default=None, alias="X-Confirm-Action"),
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Retry applying the currently published model without publishing a new configuration."""
    require_confirmation(confirm_action, "hot-switch")
    state = await state_for_read(session)
    if not state.published_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先发布模型配置")
    record = await session.scalar(select(ConfigVersion).where(ConfigVersion.version == state.published_version))
    if record is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前配置版本不存在")
    before = {"active_model_version": model_runtime.active_model_version}
    await model_runtime.hot_switch(record.payload_json["model"], record.version)
    add_audit(session, user, "model_hot_switch", "configs/model", before, {"active_model_version": model_runtime.active_model_version}, client_ip(request.headers, request.client.host if request.client else None), record.version)
    await session.commit()
    return {"config_version": record.version, "model_version": model_runtime.active_model_version}


@router.get("/{config_type}", response_model=ConfigDraftResponse)
async def get_draft(config_type: str, user: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ConfigDraftResponse:
    ensure_config_type(config_type)
    return response_for(config_type, await state_for_read(session))


@router.put("/{config_type}", response_model=ConfigDraftResponse)
async def update_draft(
    config_type: str,
    body: ConfigTypeUpdate,
    request: Request,
    confirm_action: str | None = Header(default=None, alias="X-Confirm-Action"),
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_db),
) -> ConfigDraftResponse:
    ensure_config_type(config_type)
    require_confirmation(confirm_action, "save")
    state = await state_for_update(session)
    if body.draft_revision != state.draft_revision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="草稿已更新，请重新加载")
    candidate = copy.deepcopy(state.draft_payload)
    candidate[config_type] = body.value
    errors = validate_payload(candidate)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})
    before = copy.deepcopy(state.draft_payload[config_type])
    state.draft_payload = candidate
    state.draft_revision += 1
    state.updated_by = user.id
    add_audit(session, user, "config_draft_saved", f"configs/{config_type}", before, body.value, client_ip(request.headers, request.client.host if request.client else None), state.published_version)
    await session.commit()
    return response_for(config_type, state)
