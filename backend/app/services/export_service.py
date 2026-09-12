"""
Export service — manages background export jobs with signed download tokens.
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.export_job import ExportJob, ExportJobStatus
from app.models.workspace_member import WorkspaceMember
from app.reports.generator import ReportGenerator
from app.reports.renderer import ReportRenderer
from app.repositories.base import BaseRepository
from app.storage.factory import create_storage_provider

logger = get_logger(__name__)


class ExportService:
    """Background export jobs with token-based download."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = BaseRepository(db, ExportJob)

    async def create_export(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        fmt: str,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ExportJob:
        from app.models.export_job import ExportEntityType, ExportFormat
        try:
            etype = ExportEntityType(entity_type)
            eformat = ExportFormat(fmt)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None

        job = ExportJob(
            user_id=user_id,
            workspace_id=workspace_id,
            entity_type=etype,
            entity_id=entity_id,
            format=eformat,
            status=ExportJobStatus.QUEUED,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def process_export(self, job_id: uuid.UUID) -> ExportJob:
        """Execute a queued export; called by the durable worker."""
        job = await self.repo.get(job_id)
        if not job:
            raise ValueError(f"Export job {job_id} not found")
        await self._process_export(job)
        await self.db.commit()
        return job

    async def _process_export(self, job: ExportJob) -> None:
        from datetime import datetime

        job.status = ExportJobStatus.RUNNING
        await self.db.flush()

        entity_type = job.entity_type.value if hasattr(job.entity_type, "value") else job.entity_type
        fmt = job.format.value if hasattr(job.format, "value") else job.format

        output: str | bytes = ""
        file_ext = fmt

        if entity_type in ("investigation", "report"):
            gen = ReportGenerator(self.db)
            renderer = ReportRenderer()
            data = await gen.generate(job.entity_id, job.user_id)
            if fmt == "markdown":
                output = renderer.render_markdown(data)
                file_ext = "md"
            elif fmt == "html":
                output = renderer.render_html(data)
            elif fmt == "json":
                output = renderer.render_json(data)
            else:
                output = renderer.render_markdown(data)
                file_ext = "md"
        elif entity_type == "evidence":
            output = json.dumps({"entity_id": str(job.entity_id), "format": fmt}, indent=2)
        elif entity_type == "graph":
            output = json.dumps({"entity_id": str(job.entity_id), "type": "graph"}, indent=2)
        elif entity_type == "timeline":
            output = json.dumps({"entity_id": str(job.entity_id), "type": "timeline"}, indent=2)
        else:
            raise ValueError(f"Unsupported export entity type: {entity_type}")

        filename = f"{entity_type}_{job.entity_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        payload = output if isinstance(output, bytes) else output.encode("utf-8")
        mime = "application/octet-stream"
        if file_ext == "json":
            mime = "application/json"
        elif file_ext in ("html", "md"):
            mime = "text/html" if file_ext == "html" else "text/markdown"
        stored = await create_storage_provider().store(
            payload, filename, mime, path=f"exports/{job.workspace_id}"
        )
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        job.file_path = stored.path
        job.file_size = stored.size
        job.download_token = token
        job.expires_at = expires_at
        job.status = ExportJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.locked_by = None
        job.locked_at = None
        await self.db.flush()

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> ExportJob:
        job = await self.repo.get(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
        await self._check_workspace_access(job.workspace_id, user_id)
        return job

    async def list_for_workspace(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50
    ) -> list[ExportJob]:
        await self._check_workspace_access(workspace_id, user_id)
        return await self.repo.find_many(
            workspace_id=workspace_id, order_by="created_at", descending=True, limit=limit
        )

    async def download_with_token(self, token: str) -> tuple[bytes, str, str]:
        from datetime import UTC
        job = await self.repo.find_one(download_token=token)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid download token")
        if job.status != ExportJobStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Export not yet completed")
        if job.expires_at and datetime.now(UTC) > job.expires_at:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download link has expired")
        if not job.file_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No file available")
        data = await create_storage_provider().retrieve(job.file_path)
        if data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
        extension = job.format.value if hasattr(job.format, "value") else "json"
        mime = "application/octet-stream"
        if extension == "json":
            mime = "application/json"
        elif extension == "html":
            mime = "text/html"
        elif extension in ("markdown", "md"):
            mime = "text/markdown"
        return data, f"export.{extension}", mime

    async def _check_workspace_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member_repo = BaseRepository(self.db, WorkspaceMember)
        member = await member_repo.find_one(workspace_id=workspace_id, user_id=user_id)
        if not member:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
