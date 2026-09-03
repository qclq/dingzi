import asyncio
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.detection import Detection
from app.models.export import ExportJob
from app.repositories.detection import filtered_detections
from app.services.files import presign_download

EXPORT_BATCH_SIZE = 1_000


def serialise_query(query: dict) -> dict:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in query.items()
        if value is not None and value != []
    }


def create_export_job(session: AsyncSession, *, user_id: int, payload: dict) -> ExportJob:
    job = ExportJob(
        id=str(uuid4()),
        created_by_id=user_id,
        format=payload["format"],
        query=serialise_query(payload),
        status="queued",
    )
    session.add(job)
    return job


def job_download_url(job: ExportJob) -> str | None:
    if job.status != "completed" or not job.file_path or not job.expires_at:
        return None
    expires_at = job.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return None
    return presign_download(get_settings(), job.file_path)[0]


def _query_values(query: dict) -> tuple[datetime | None, datetime | None, str | None, str | None, str | None, str | None, list[int]]:
    start = datetime.fromisoformat(query["start_time"]) if query.get("start_time") else None
    end = datetime.fromisoformat(query["end_time"]) if query.get("end_time") else None
    return (
        start,
        end,
        query.get("result"),
        query.get("operator"),
        query.get("image_id"),
        query.get("line_id"),
        query.get("detection_ids", []),
    )


async def _matching_detections(session: AsyncSession, query: dict, offset: int) -> list[Detection]:
    start, end, result, operator, image_id, line_id, ids = _query_values(query)
    statement = filtered_detections(start, end, result, operator, image_id, line_id)
    if ids:
        statement = statement.where(Detection.id.in_(ids))
    rows = await session.scalars(
        statement.order_by(Detection.captured_at.desc(), Detection.id.desc())
        .offset(offset)
        .limit(EXPORT_BATCH_SIZE)
    )
    return list(rows)


async def _count_matching(session: AsyncSession, query: dict) -> int:
    start, end, result, operator, image_id, line_id, ids = _query_values(query)
    statement = filtered_detections(start, end, result, operator, image_id, line_id)
    if ids:
        statement = statement.where(Detection.id.in_(ids))
    total = await session.scalar(select(func.count()).select_from(statement.subquery()))
    return int(total or 0)


def _row(detection: Detection) -> list[object]:
    return [
        detection.image_id,
        detection.captured_at.isoformat(),
        detection.operator,
        detection.defect_count,
        detection.result,
        detection.model_version,
        detection.config_version,
        detection.mes_status,
        detection.inference_ms,
    ]


def _write_pdf(html: str, output_path: Path) -> None:
    try:
        from weasyprint import HTML

        HTML(string=html).write_pdf(output_path)
    except (ImportError, OSError):
        # Windows developer hosts may not have Pango/GLib. Production images install them
        # and always take the WeasyPrint branch; this small valid PDF keeps mock demos usable.
        message = b"Phase 4 PDF preview - install WeasyPrint native runtime for full rendering"
        stream = b"BT /F1 10 Tf 40 760 Td (" + message + b") Tj ET"
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        content = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(content))
            content.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(content)
        content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
        content.extend(b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]))
        content.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )
        output_path.write_bytes(content)


async def generate_export(session: AsyncSession, export_id: str) -> None:
    job = await session.get(ExportJob, export_id)
    if job is None or job.status not in {"queued", "running"}:
        return
    job.status = "running"
    await session.commit()
    try:
        settings = get_settings()
        output_dir = Path(settings.export_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = "xlsx" if job.format == "xlsx" else "pdf"
        output_path = output_dir / f"detection-export-{job.id}.{suffix}"
        total = await _count_matching(session, job.query)
        if job.format == "xlsx":
            from openpyxl import Workbook

            workbook = Workbook(write_only=True)
            sheet = workbook.create_sheet("检测记录")
            sheet.append(["图片编号", "检测时间", "操作员", "缺陷数量", "结果", "模型版本", "配置版本", "MES状态", "推理耗时(ms)"])
            for offset in range(0, total, EXPORT_BATCH_SIZE):
                for detection in await _matching_detections(session, job.query, offset):
                    sheet.append(_row(detection))
            workbook.save(output_path)
        else:
            rows: list[str] = []
            for offset in range(0, total, EXPORT_BATCH_SIZE):
                rows.extend(
                    "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in _row(detection)) + "</tr>"
                    for detection in await _matching_detections(session, job.query, offset)
                )
            html = "<h1>定子冲片检测记录</h1><table><thead><tr><th>图片编号</th><th>检测时间</th><th>操作员</th><th>缺陷数</th><th>结果</th><th>模型</th><th>配置</th><th>MES</th><th>推理毫秒</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
            _write_pdf(html, output_path)
        job.record_count = total
        job.file_path = str(output_path)
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.expires_at = datetime.now(UTC) + timedelta(hours=24)
    except Exception as exc:  # noqa: BLE001  # Celery boundary persists all task failures
        job.status = "failed"
        job.error_message = str(exc)[:2_000]
    await session.commit()


def run_export_sync(export_id: str) -> None:
    from app.db.session import SessionLocal

    async def run() -> None:
        async with SessionLocal() as session:
            await generate_export(session, export_id)

    asyncio.run(run())


def mark_export_dispatch_failed_sync(export_id: str) -> None:
    from app.db.session import SessionLocal

    async def mark_failed() -> None:
        async with SessionLocal() as session:
            job = await session.get(ExportJob, export_id)
            if job is not None and job.status == "queued":
                job.status = "failed"
                job.error_message = "异步任务队列不可用，请稍后重试"
                await session.commit()

    asyncio.run(mark_failed())
