from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.system import DetectionFile, MesDelivery, SystemLog, SystemSetting

DEFAULT_MES = {"mes_url": None, "auth_token": None, "auto_report": False}
DEFAULT_FILE_POLICY = {"retention_days": 90, "quota_gb": None, "warning_percent": 80}


async def setting(session: AsyncSession, key: str, default: dict) -> SystemSetting:
    item = await session.get(SystemSetting, key)
    if item is None:
        item = SystemSetting(key=key, value=default.copy(), revision=1)
        session.add(item); await session.flush()
    return item


def redacted_mes(item: SystemSetting) -> dict:
    return {"mes_url": item.value.get("mes_url"), "auto_report": bool(item.value.get("auto_report")), "revision": item.revision, "token_configured": bool(item.value.get("auth_token"))}


def audit(session: AsyncSession, actor_id: int | None, action: str, resource: str, before: dict | None, after: dict | None, ip: str | None, *, level: str = "INFO", source: str = "system", message: str | None = None) -> None:
    session.add(AuditLog(actor_id=actor_id, action=action, resource=resource, before_json=before, after_json=after, ip_address=ip, level=level, source=source, message=message))


def system_log(session: AsyncSession, level: str, source: str, message: str, context: dict | None = None) -> None:
    session.add(SystemLog(level=level, source=source, message=message, context=context))


class MesClient:
    async def test_connection(self, url: str, token: str | None) -> dict: raise NotImplementedError
    async def report(self, url: str, token: str | None, payload: dict, idempotency_key: str) -> dict: raise NotImplementedError


class HttpMesClient(MesClient):
    async def _request(self, method: str, url: str, token: str | None, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        if token: headers["Authorization"] = f"Bearer {token}"
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10, connect=3), follow_redirects=False) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
            return {"connected": 200 <= response.status_code < 300, "http_status": response.status_code, "response_time_ms": round((perf_counter()-started)*1000), "error_message": None if response.is_success else response.text[:500]}
        except httpx.HTTPError as exc:
            return {"connected": False, "http_status": None, "response_time_ms": round((perf_counter()-started)*1000), "error_message": str(exc)[:500]}
    async def test_connection(self, url: str, token: str | None) -> dict: return await self._request("GET", url, token)
    async def report(self, url: str, token: str | None, payload: dict, idempotency_key: str) -> dict: return await self._request("POST", url, token, json=payload, headers={"Idempotency-Key": idempotency_key})


class MockMesClient(MesClient):
    async def test_connection(self, url: str, token: str | None) -> dict: return {"connected": True, "http_status": 200, "response_time_ms": 1, "error_message": None}
    async def report(self, url: str, token: str | None, payload: dict, idempotency_key: str) -> dict: return {"connected": True, "http_status": 200, "response_time_ms": 1, "error_message": None}


def mes_client(url: str) -> MesClient: return MockMesClient() if url.startswith("mock://") else HttpMesClient()


async def dispatch_delivery(session: AsyncSession, delivery_id: int) -> None:
    delivery = await session.get(MesDelivery, delivery_id)
    if delivery is None or delivery.status == "succeeded": return
    config = await setting(session, "mes", DEFAULT_MES)
    url, token = config.value.get("mes_url"), config.value.get("auth_token")
    if not url or not token:
        delivery.status = "failed"; delivery.last_error = "MES 未配置"; await session.commit(); return
    delivery.status = "sending"; delivery.attempts += 1; await session.commit()
    result = await mes_client(url).report(url, token, delivery.payload, delivery.idempotency_key)
    delivery.last_status_code, delivery.last_error = result["http_status"], result["error_message"]
    if result["connected"]:
        delivery.status = "succeeded"
    elif delivery.attempts <= 3:
        delivery.status = "retry_wait"; delivery.next_attempt_at = datetime.now(UTC) + timedelta(seconds=5 * 2 ** (delivery.attempts - 1))
    else:
        delivery.status = "failed"; system_log(session, "ERROR", "mes", "MES 上报失败", {"delivery_id": delivery.id})
    await session.commit()


async def cleanup_files(session: AsyncSession) -> int:
    policy = await setting(session, "file_policy", DEFAULT_FILE_POLICY)
    cutoff = datetime.now(UTC) - timedelta(days=int(policy.value["retention_days"]))
    rows = list((await session.scalars(select(DetectionFile).where(DetectionFile.deleted_at.is_(None), DetectionFile.created_at < cutoff).order_by(DetectionFile.created_at, DetectionFile.id))).all())
    count = 0
    for item in rows:
        try:
            path = Path(item.uri)
            if path.is_file(): path.unlink()
            item.deleted_at = datetime.now(UTC); item.delete_reason = "retention"; count += 1
        except OSError as exc: system_log(session, "ERROR", "files", "文件清理失败", {"file_id": item.id, "error": str(exc)[:200]})
    if count: system_log(session, "INFO", "files", "文件保留期清理完成", {"count": count})
    quota_gb = policy.value.get("quota_gb")
    if quota_gb:
        quota = int(float(quota_gb) * 1_000_000_000)
        used = int(await session.scalar(select(func.coalesce(func.sum(DetectionFile.size_bytes), 0)).where(DetectionFile.deleted_at.is_(None))) or 0)
        warning = quota * int(policy.value.get("warning_percent", 80)) // 100
        if used >= warning:
            system_log(session, "WARNING", "files", "文件配额达到预警阈值", {"used_bytes": used, "quota_bytes": quota})
        if used >= quota:
            candidates = list((await session.scalars(select(DetectionFile).where(DetectionFile.deleted_at.is_(None)).order_by(DetectionFile.created_at, DetectionFile.id))).all())
            for item in candidates:
                if used < quota:
                    break
                try:
                    path = Path(item.uri)
                    if path.is_file():
                        path.unlink()
                    item.deleted_at = datetime.now(UTC); item.delete_reason = "quota"; used -= item.size_bytes; count += 1
                except OSError as exc:
                    system_log(session, "ERROR", "files", "文件配额清理失败", {"file_id": item.id, "error": str(exc)[:200]})
    await session.commit(); return count
