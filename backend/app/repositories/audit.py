from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit(session: AsyncSession, actor_id: int | None, action: str, ip_address: str | None = None) -> None:
    session.add(AuditLog(actor_id=actor_id, action=action, resource="auth", ip_address=ip_address))
