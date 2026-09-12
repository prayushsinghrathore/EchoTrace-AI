"""Durable PostgreSQL-backed worker for AI and export jobs.

Workers are stateless. PostgreSQL owns queue state, leases, retries, and
results, allowing multiple worker processes or pods to run concurrently.
"""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select

from app.ai.jobs import _execute_job
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.ai_job import AIJob, AIJobStatus
from app.models.export_job import ExportJob, ExportJobStatus
from app.services.export_service import ExportService

logger = get_logger(__name__)
WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
POLL_SECONDS = 2
LEASE_SECONDS = max(settings.AI_TIMEOUT_SECONDS + 60, 180)


async def recover_stale_jobs() -> None:
    """Return abandoned leases to the queue after a worker crash."""
    cutoff = datetime.now(UTC) - timedelta(seconds=LEASE_SECONDS)
    async with AsyncSessionLocal() as db:
        for model, status in ((AIJob, AIJobStatus), (ExportJob, ExportJobStatus)):
            result = await db.execute(
                select(model).where(model.status == status.RUNNING, model.locked_at < cutoff)
            )
            for raw_job in result.scalars():
                job: Any = raw_job  # SQLAlchemy's generic model type is dynamic here.
                if job.attempts >= job.max_attempts:
                    job.status = status.FAILED
                    job.error = "Worker lease expired after maximum attempts"
                else:
                    job.status = status.QUEUED
                    job.available_at = datetime.now(UTC)
                job.locked_at = None
                job.locked_by = None
        await db.commit()


async def claim_job(model: Any, queued_status: Any) -> uuid.UUID | None:
    """Atomically claim one available job using row-level locking."""
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        stmt = (
            select(model)
            .where(
                model.status == queued_status,
                model.locked_by.is_(None),
                or_(model.available_at.is_(None), model.available_at <= now),
            )
            .order_by(model.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = (await db.execute(stmt)).scalar_one_or_none()
        if not job:
            return None
        job.locked_by = WORKER_ID
        job.locked_at = now
        await db.commit()
        return job.id


async def run_ai_job(job_id: uuid.UUID) -> None:
    try:
        await _execute_job(job_id, WORKER_ID)
    except Exception:
        logger.exception("Unhandled AI worker failure", job_id=str(job_id))
        await release_or_fail(AIJob, AIJobStatus, job_id)


async def run_export_job(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(ExportJob, job_id)
        if not job:
            return
        if job.locked_by != WORKER_ID:
            return
        job.status = ExportJobStatus.RUNNING
        job.attempts += 1
        await db.commit()
        try:
            await ExportService(db).process_export(job_id)
        except Exception as exc:
            logger.exception("Export worker failure", job_id=str(job_id))
            if job.attempts >= job.max_attempts:
                job.status = ExportJobStatus.FAILED
                job.error = str(exc)[:1000]
            else:
                job.status = ExportJobStatus.QUEUED
                job.available_at = datetime.now(UTC) + timedelta(seconds=2 ** job.attempts)
            job.locked_by = None
            job.locked_at = None
            await db.commit()


async def release_or_fail(model: Any, status: Any, job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(model, job_id)
        if not job:
            return
        if job.attempts >= job.max_attempts:
            job.status = status.FAILED
            job.error = "Worker execution failed after maximum attempts"
        else:
            job.status = status.QUEUED
            job.available_at = datetime.now(UTC) + timedelta(seconds=2 ** job.attempts)
        job.locked_by = None
        job.locked_at = None
        await db.commit()


async def run_worker() -> None:
    logger.info("Starting durable worker", worker_id=WORKER_ID)
    await recover_stale_jobs()
    while True:
        ai_id = await claim_job(AIJob, AIJobStatus.QUEUED)
        if ai_id:
            await run_ai_job(ai_id)
            continue
        export_id = await claim_job(ExportJob, ExportJobStatus.QUEUED)
        if export_id:
            await run_export_job(export_id)
            continue
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
