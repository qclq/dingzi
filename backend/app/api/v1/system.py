import csv
import io
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.system import DetectionFile, MesDelivery, PasswordResetRequest, SystemLog
from app.models.user import User
from app.schemas.system import (
    BatchStatusUpdate,
    FilePolicy,
    FilePolicyUpdate,
    FileUsage,
    LogItem,
    LogPage,
    ManagedUser,
    MesConfig,
    MesConfigUpdate,
    MesDeliveryView,
    MesTestRequest,
    MesTestResult,
    StatusUpdate,
    UserCreate,
    UserPage,
    UserUpdate,
)
from app.security.auth import hash_password, token_hash
from app.services.system import (
    DEFAULT_FILE_POLICY,
    DEFAULT_MES,
    HttpMesClient,
    audit,
    cleanup_files,
    redacted_mes,
    setting,
)

router = APIRouter(prefix="/system", tags=["system"])


def client_ip(request: Request) -> str | None:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip() or None


def user_view(user: User) -> ManagedUser:
    return ManagedUser.model_validate(user, from_attributes=True)


@router.get("/admin-check")
async def admin_check(_: User = Depends(require_roles("admin"))) -> dict[str, str]:
    return {"status": "ok", "scope": "admin"}


@router.get("/users", response_model=UserPage)
async def list_users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), keyword: str | None = None, role: str | None = None, user_status: str | None = Query(None, alias="status"), _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> UserPage:
    clauses = [User.deleted_at.is_(None)]
    if keyword: clauses.append(or_(User.username.contains(keyword), User.display_name.contains(keyword), User.email.contains(keyword)))
    if role: clauses.append(User.role == role)
    if user_status: clauses.append(User.status == user_status)
    where = and_(*clauses); total = int(await session.scalar(select(func.count()).select_from(User).where(where)) or 0)
    rows = list((await session.scalars(select(User).where(where).order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    return UserPage(items=[user_view(row) for row in rows], total=total, page=page, page_size=page_size)


@router.post("/users", response_model=ManagedUser, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ManagedUser:
    if await session.scalar(select(User).where(User.username == body.username)): raise HTTPException(409, "账号已存在")
    try: password_hash = hash_password(body.password)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    user = User(username=body.username, password_hash=password_hash, display_name=body.display_name, email=str(body.email) if body.email else None, role=body.role)
    session.add(user); await session.flush(); audit(session, admin.id, "user_created", f"users/{user.id}", None, {"username": user.username, "role": user.role}, client_ip(request)); await session.commit(); await session.refresh(user)
    return user_view(user)


async def protect_last_admin(session: AsyncSession, target: User, *, role: str | None = None, user_status: str | None = None, deleted: bool = False) -> None:
    if target.role != "admin" or not (deleted or role == "operator" or user_status == "disabled"): return
    others = int(await session.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.status == "active", User.deleted_at.is_(None), User.id != target.id)) or 0)
    if not others: raise HTTPException(409, "至少保留一个启用的管理员")


@router.put("/users/{user_id}", response_model=ManagedUser)
async def update_user(user_id: int, body: UserUpdate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ManagedUser:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at: raise HTTPException(404, "用户不存在")
    if user.revision != body.revision: raise HTTPException(409, "用户已更新，请重新加载")
    await protect_last_admin(session, user, role=body.role, user_status=body.status)
    before = {"display_name": user.display_name, "email": user.email, "role": user.role, "status": user.status}
    if body.display_name is not None: user.display_name = body.display_name
    if body.email is not None: user.email = str(body.email)
    if body.role is not None: user.role = body.role
    if body.status is not None: user.status = body.status
    if body.role is not None or body.status is not None: user.credential_version += 1
    user.revision += 1; audit(session, admin.id, "user_updated", f"users/{user.id}", before, {"display_name": user.display_name, "email": user.email, "role": user.role, "status": user.status}, client_ip(request)); await session.commit()
    return user_view(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> None:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at: raise HTTPException(404, "用户不存在")
    if user.id == admin.id: raise HTTPException(409, "不能删除当前账号")
    await protect_last_admin(session, user, deleted=True); user.deleted_at = datetime.now(UTC); user.status = "disabled"; user.credential_version += 1; user.revision += 1
    audit(session, admin.id, "user_deleted", f"users/{user.id}", {"username": user.username}, None, client_ip(request)); await session.commit()


@router.post("/users/{user_id}/status", response_model=ManagedUser)
async def set_user_status(user_id: int, body: StatusUpdate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ManagedUser:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at: raise HTTPException(404, "用户不存在")
    if user.id == admin.id and body.status == "disabled": raise HTTPException(409, "不能停用当前账号")
    await protect_last_admin(session, user, user_status=body.status); user.status = body.status; user.credential_version += 1; user.revision += 1
    audit(session, admin.id, "user_status_updated", f"users/{user.id}", None, {"status": body.status}, client_ip(request)); await session.commit(); return user_view(user)


@router.post("/users/batch-status")
async def batch_status(body: BatchStatusUpdate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> dict[str, int]:
    rows = list((await session.scalars(select(User).where(User.id.in_(body.user_ids), User.deleted_at.is_(None)))).all())
    if len(rows) != len(set(body.user_ids)): raise HTTPException(404, "存在不存在的用户")
    for user in rows:
        if user.id == admin.id and body.status == "disabled": raise HTTPException(409, "不能停用当前账号")
        await protect_last_admin(session, user, user_status=body.status)
    for user in rows: user.status = body.status; user.credential_version += 1; user.revision += 1
    audit(session, admin.id, "users_batch_status", "users", None, {"count": len(rows), "status": body.status}, client_ip(request)); await session.commit(); return {"updated": len(rows)}


@router.post("/users/{user_id}/unlock", response_model=ManagedUser)
async def unlock_user(user_id: int, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> ManagedUser:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at: raise HTTPException(404, "用户不存在")
    user.locked_until = None; user.failed_login_attempts = 0; user.revision += 1; audit(session, admin.id, "user_unlocked", f"users/{user.id}", None, {"username": user.username}, client_ip(request)); await session.commit(); return user_view(user)


@router.post("/users/{user_id}/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(user_id: int, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    user = await session.get(User, user_id)
    if user is None or user.deleted_at: raise HTTPException(404, "用户不存在")
    if not user.email: raise HTTPException(422, "该用户没有预留邮箱")
    token = token_urlsafe(32)
    reset = PasswordResetRequest(user_id=user.id, token_hash=token_hash(token), expires_at=datetime.now(UTC) + timedelta(minutes=30))
    session.add(reset); audit(session, admin.id, "password_reset_requested", f"users/{user.id}", None, {"email": user.email}, client_ip(request)); await session.commit()
    # SMTP delivery is configured by deployment; the token is deliberately never returned by this API.
    return {"message": "密码重置请求已创建；配置 SMTP 后才能发送邮件"}


async def list_logs(model, page: int, page_size: int, start_time: datetime | None, end_time: datetime | None, level: str | None, source: str | None, keyword: str | None, session: AsyncSession) -> LogPage:
    filters = []
    if start_time: filters.append(model.created_at >= start_time)
    if end_time: filters.append(model.created_at < end_time)
    if level: filters.append(model.level == level)
    if source: filters.append(model.source == source)
    if keyword: filters.append(or_(model.message.contains(keyword), model.source.contains(keyword), getattr(model, "action", model.source).contains(keyword)))
    where = and_(*filters) if filters else True; total = int(await session.scalar(select(func.count()).select_from(model).where(where)) or 0)
    rows = list((await session.scalars(select(model).where(where).order_by(model.created_at.desc(), model.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    return LogPage(items=[LogItem(id=row.id, level=row.level, source=row.source, message=row.message, actor_id=getattr(row, "actor_id", None), action=getattr(row, "action", None), resource=getattr(row, "resource", None), ip_address=getattr(row, "ip_address", None), created_at=row.created_at) for row in rows], total=total, page=page, page_size=page_size)


@router.get("/audit-logs", response_model=LogPage)
async def audit_logs(page: int = 1, page_size: int = Query(20, le=100), start_time: datetime | None = None, end_time: datetime | None = None, level: str | None = None, source: str | None = None, keyword: str | None = None, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> LogPage:
    return await list_logs(AuditLog, page, page_size, start_time, end_time, level, source, keyword, session)


@router.get("/system-logs", response_model=LogPage)
async def system_logs(page: int = 1, page_size: int = Query(20, le=100), start_time: datetime | None = None, end_time: datetime | None = None, level: str | None = None, source: str | None = None, keyword: str | None = None, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> LogPage:
    return await list_logs(SystemLog, page, page_size, start_time, end_time, level, source, keyword, session)


@router.get("/logs/{kind}/csv")
async def export_logs_csv(kind: str, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    model = AuditLog if kind == "audit" else SystemLog if kind == "system" else None
    if model is None: raise HTTPException(404, "未知日志类型")
    rows = list((await session.scalars(select(model).order_by(model.created_at.desc()).limit(100_000))).all())
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["ID", "时间", "级别", "来源", "内容", "操作", "资源", "IP"])
    for row in rows: writer.writerow([row.id, row.created_at.isoformat(), row.level, row.source, row.message or "", getattr(row, "action", ""), getattr(row, "resource", ""), getattr(row, "ip_address", "")])
    return StreamingResponse(iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{kind}-logs.csv"'})


@router.get("/mes/config", response_model=MesConfig)
async def get_mes(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> MesConfig:
    return MesConfig(**redacted_mes(await setting(session, "mes", DEFAULT_MES)))


@router.put("/mes/config", response_model=MesConfig)
async def update_mes(body: MesConfigUpdate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> MesConfig:
    item = await setting(session, "mes", DEFAULT_MES)
    if item.revision != body.revision: raise HTTPException(409, "MES 配置已更新")
    before = redacted_mes(item); item.value = {"mes_url": str(body.mes_url) if body.mes_url else None, "auth_token": body.auth_token if body.auth_token is not None else item.value.get("auth_token"), "auto_report": body.auto_report}; item.revision += 1; item.updated_by = admin.id
    audit(session, admin.id, "mes_config_updated", "mes", before, redacted_mes(item), client_ip(request)); await session.commit(); return MesConfig(**redacted_mes(item))


@router.post("/mes/test-connection", response_model=MesTestResult)
async def test_mes(body: MesTestRequest, _: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> MesTestResult:
    saved = await setting(session, "mes", DEFAULT_MES); url = str(body.mes_url) if body.mes_url else saved.value.get("mes_url"); token = body.auth_token if body.auth_token is not None else saved.value.get("auth_token")
    if not url: raise HTTPException(422, "请提供 MES URL")
    return MesTestResult(**await HttpMesClient().test_connection(url, token))


@router.get("/mes/deliveries", response_model=list[MesDeliveryView])
async def list_deliveries(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> list[MesDeliveryView]:
    rows = list((await session.scalars(select(MesDelivery).order_by(MesDelivery.created_at.desc()).limit(200))).all()); return [MesDeliveryView.model_validate(row, from_attributes=True) for row in rows]


@router.post("/mes/manual-report", status_code=status.HTTP_202_ACCEPTED)
async def manual_report(detection_id: int, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), request: Request = None, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> dict[str, object]:
    if not idempotency_key: raise HTTPException(400, "人工补报需要 Idempotency-Key")
    existing = await session.scalar(select(MesDelivery).where(MesDelivery.idempotency_key == idempotency_key))
    if existing: return {"delivery_id": existing.id, "status": existing.status}
    from app.models.detection import Detection
    detection = await session.get(Detection, detection_id)
    if detection is None: raise HTTPException(404, "检测记录不存在")
    row = await session.scalar(select(MesDelivery).where(MesDelivery.detection_id == detection_id))
    if row and row.status == "succeeded": raise HTTPException(409, "该记录已上报成功")
    if row is None:
        row = MesDelivery(detection_id=detection.id, idempotency_key=idempotency_key, payload={"image_id": detection.image_id, "result": detection.result, "captured_at": detection.captured_at.isoformat(), "defect_count": detection.defect_count})
        session.add(row)
    else: row.status = "pending"; row.attempts = 0; row.idempotency_key = idempotency_key
    await session.flush(); audit(session, admin.id, "mes_manual_report", f"detections/{detection_id}", None, {"delivery_id": row.id}, client_ip(request)); await session.commit()
    from app.tasks.mes import deliver_mes
    try:
        deliver_mes.delay(row.id)
    except (ConnectionError, OSError):
        # The persisted outbox row will be collected by the periodic worker.
        pass
    return {"delivery_id": row.id, "status": row.status}


@router.get("/file-policy", response_model=FilePolicy)
async def get_file_policy(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> FilePolicy:
    item = await setting(session, "file_policy", DEFAULT_FILE_POLICY); return FilePolicy(**item.value, revision=item.revision)


@router.put("/file-policy", response_model=FilePolicy)
async def update_file_policy(body: FilePolicyUpdate, request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> FilePolicy:
    item = await setting(session, "file_policy", DEFAULT_FILE_POLICY)
    if item.revision != body.revision: raise HTTPException(409, "文件策略已更新")
    before = item.value.copy(); item.value = body.model_dump(exclude={"revision"}); item.revision += 1; item.updated_by = admin.id; audit(session, admin.id, "file_policy_updated", "file-policy", before, item.value, client_ip(request)); await session.commit(); return FilePolicy(**item.value, revision=item.revision)


@router.get("/file-policy/usage", response_model=FileUsage)
async def file_usage(_: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> FileUsage:
    item = await setting(session, "file_policy", DEFAULT_FILE_POLICY); used = int(await session.scalar(select(func.coalesce(func.sum(DetectionFile.size_bytes), 0)).where(DetectionFile.deleted_at.is_(None))) or 0); count = int(await session.scalar(select(func.count()).select_from(DetectionFile).where(DetectionFile.deleted_at.is_(None))) or 0); quota = int(item.value["quota_gb"] * 1_000_000_000) if item.value.get("quota_gb") else None
    return FileUsage(used_bytes=used, quota_bytes=quota, percent=round(used / quota * 100, 2) if quota else None, file_count=count)


@router.post("/file-policy/cleanup")
async def manual_cleanup(request: Request, admin: User = Depends(require_roles("admin")), session: AsyncSession = Depends(get_db)) -> dict[str, int]:
    count = await cleanup_files(session); audit(session, admin.id, "file_cleanup_manual", "file-policy", None, {"count": count}, client_ip(request)); await session.commit(); return {"deleted": count}
